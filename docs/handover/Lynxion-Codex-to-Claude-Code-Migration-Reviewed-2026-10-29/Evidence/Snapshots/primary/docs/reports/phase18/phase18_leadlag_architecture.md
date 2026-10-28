# Phase 18 — Cross-Exchange & Lead-Lag Microstructure: Architecture & Method

**Date:** 2026-06-13. Analysis only. No existing strategy/parameter/threshold/risk/execution modified; no
profitability assumed; Phases 1–17 conclusions not overwritten. This file documents the cross-venue data
layer and the lead-lag methodology; results are in the per-test files and `phase18_final_verdict.md`.

## Question

Phase 17 found single-venue microstructure (order flow / liquidity / funding×flow) carries no incremental
edge beyond OHLCV. Phase 18 asks a different question: does **temporal precedence between markets** — one
venue or asset *moving first* — contain predictive information that a single OHLCV series cannot, and is
any such lead-lag exploitable net of cost?

Lead-lag is a **fine-timescale** phenomenon (price discovery races resolve in seconds–minutes), so this
phase uses **1-minute** data; coarser bars make everything look contemporaneous.

## Data layer (cross-venue, 1-minute, common UTC grid)

Fetched via `scripts/fetch_xvenue.py` (binance-style kline payloads; MEXC spot v3 mirrors Binance), stored
at `data/history/xvenue/<venue>/<SYM>-USDT.csv` (`timestamp,close,volume`), ~90 days, BTC/ETH/SOL:

| Venue | Market | Role |
|---|---|---|
| `binance_fut` | Binance perpetual futures | home venue; cross-asset lead-lag; perp side of basis |
| `binance_spot` | Binance spot | perp-spot lead-lag & basis |
| `mexc_spot` | MEXC spot | cross-exchange lead-lag & dispersion |

All series are inner-joined on timestamp so every comparison is on the **same minute** across venues.

## Three a-priori tests (no tuning)

**T1 — Cross-asset lead-lag (does BTC lead ETH / SOL?)** on Binance futures.
Lagged cross-correlation `corr(BTC_ret[t−k], ALT_ret[t])`, k=0..3; tradable signal = take the ALT in the
direction of BTC's *previous* bar (1-min lead, no lookahead). *Note: cross-asset relationships are
partly OHLCV-derived (Phase-13 flagged cross-asset as low-uniqueness); the genuinely-new content here is
the temporal precedence, not the level.*

**T2 — Perp-spot lead-lag & basis** (Binance fut vs Binance spot, same symbol).
Who leads (CCF both directions); basis `=(perp−spot)/spot`; IC of basis vs next-bar perp return.
Perp-spot relationships are **not** a single-OHLCV transform (two markets) → genuinely cross-market.

**T3 — Cross-exchange lead-lag & dispersion** (Binance fut vs MEXC spot, same symbol).
Who leads (CCF both directions); dispersion `=(binance−mexc)/mexc`; IC of dispersion vs next-bar MEXC
return (reversion-to-consensus). Genuinely cross-venue (requires multi-exchange data).

## Evaluation contract (carried from prior phases)

- **Information content (cost-free):** lagged cross-correlation (the lead-lag measure) and Spearman IC of
  basis/dispersion vs forward return. Contemporaneous (k=0) correlation is reported alongside the lead
  (k≥1) correlation — only the **lead** part is predictive; a high k=0 with ~0 k=1 means the markets are
  contemporaneous/arbitraged (no exploitable lead).
- **Cost-adjusted deployability:** leader→laggard directional signal, net of **0.30% round-trip**
  (unchanged), with **gross** expectancy reported separately so information is visible apart from cost.
- **4-fold walk-forward**, **per-symbol** BTC/ETH/SOL, **cross-symbol** robustness.

## What is in and out of scope (honest)

- **In scope (buildable historically):** cross-asset, perp-spot, and cross-exchange lead-lag at 1-minute
  from integrated REST kline endpoints.
- **Out of scope / not claimed:** sub-minute (tick/latency-arb) lead-lag — the regime where cross-venue
  price discovery actually races — is **not** observable at 1-minute granularity and is not a strategy
  this system could execute (it would require co-located low-latency infrastructure). A 1-minute null
  result therefore bounds *minute-scale* lead-lag, **not** HFT-scale lead-lag, which is explicitly outside
  this system's reach and this phase's claim.

Results → `cross_asset_leadlag_analysis.md`, `cross_exchange_basis_analysis.md`,
`leadlag_walkforward_results.md`; verdict → `phase18_final_verdict.md`. Harness:
`scripts/phase18_leadlag_analysis.py`.
