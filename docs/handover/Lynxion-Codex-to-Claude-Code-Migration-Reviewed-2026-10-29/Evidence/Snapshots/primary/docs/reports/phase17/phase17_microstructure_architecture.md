# Phase 17 — Microstructure Data Architecture

**Date:** 2026-06-13. Analysis only. No existing strategy/parameter/threshold/risk/execution code
modified; no profitability assumed. This file documents the **non-OHLCV microstructure data layer** built
for Phase 17, what is genuinely buildable/backtestable from integrated sources, and what is structurally
blocked. It does not overwrite any Phase 1–16 conclusion.

## Design principle

Phases 1–16 established there is no persistent edge in OHLCV-derived feature space. Phase 17 therefore
sources signal **only** from data that is **not derivable from open/high/low/close/volume**. OHLCV is used
strictly as a contextual baseline (e.g. to compute forward returns for evaluation and a momentum baseline
for an incremental-information check) — **never as a signal driver.**

## The key enabler: order-flow fields inside Binance klines

Plain OHLCV CSVs (used in all prior phases) discard fields that the Binance **futures** kline endpoint
actually returns. Each kline carries 12 fields; beyond OHLCV we retain:

| Field | Meaning | Why it is non-OHLCV |
|---|---|---|
| `[8]` num_trades | count of trades in the bar | trade *structure*, not in OHLCV |
| `[9]` taker_buy_base | **aggressor-buy** base volume | aggressor side is invisible in OHLCV (volume has no sign) |
| `[10]` taker_buy_quote | aggressor-buy quote volume | same, quote-denominated |

From these, **aggressor order flow is reconstructable historically and for free**, at any timeframe — the
single most important fact enabling a rigorous microstructure backtest. Source: Binance **FUTURES**
(`fapi`) klines — funding-aligned (perp) and where crypto microstructure volume concentrates.

**Stored layer:** `data/history/micro/<tf>/<SYM>-USDT.csv` with
`timestamp,open,high,low,close,volume,num_trades,taker_buy_base,taker_buy_quote`.
Fetcher: `scripts/fetch_microstructure.py`. Window: **5m, ~2 years (2024-06 → 2026-06), BTC/ETH/SOL** —
~210k bars/symbol (ample for 4-fold walk-forward across multiple regimes).

## Derived feature definitions (a-priori, NOT tuned)

Order flow (Domain 1):
- per-bar **aggressor imbalance** `imb = (2·taker_buy_base − volume) / volume ∈ [−1, 1]`
- **flow_k** = mean(`imb`) over last `K=6` bars (30 min) — smoothed order-flow pressure
- per-bar **delta** = `2·taker_buy_base − volume`; **CVD** = cumulative delta

Liquidity microstructure (Domain 2 — trade-structure proxy):
- **intensity_z** = z-score of `num_trades` over a `Z_WIN=100`-bar window → liquidity *expansion* (high)
  vs *contraction* (low)
- **avgtrade_z** = z-score of avg trade size (`volume/num_trades`) → block/stacking vs fragmentation

Funding × Flow interaction (Domain 4):
- funding (8h, on disk, Phase-14) **forward-filled** to each 5m bar (last-known, **no lookahead**)
- funding regime (extreme_pos ≥ p90 / extreme_neg ≤ p10) crossed with `flow_k` sign

All constants (`K=6`, `HORIZON=6`, `Z_WIN=100`, percentile thresholds) are **fixed a-priori**, not
optimised — consistent with the no-tuning mandate.

## What is buildable vs blocked (honest source audit)

| Domain | Component | Buildable / backtestable? | Basis |
|---|---|---|---|
| 1 Order flow | aggressor imbalance, CVD, trade clustering | ✅ **YES** | klines `[9]`/`[8]`, full history, free |
| 2 Liquidity | trade-intensity / trade-size structure | ✅ **YES (proxy)** | klines `[8]`, `[5]/[8]` |
| 2 Liquidity | true L2 order-book imbalance, resting depth, spread | ❌ **BLOCKED (history)** | REST `/depth` is a snapshot only; no historical book from any integrated source (Phase-13) |
| 3 Liquidations | liquidation clusters, forced-deleverage cascades | ❌ **BLOCKED (history)** | Binance public `allForceOrders` backfill removed; only a live WS `forceOrder` stream — no history to backtest (Phase-13) |
| 4 Funding×Flow | funding regime × flow imbalance | ✅ **YES** | funding on disk + flow layer |

**Consequence:** Phase 17 can rigorously test **order flow (Domain 1)**, a **trade-structure liquidity
proxy (Domain 2)**, and the **funding×flow interaction (Domain 4)** on real multi-year data. True L2
order-book microstructure and historical liquidations are **backtest-blocked** — they have no integrated
historical source, so any claim about them could only be made from forward-recorded data we do not have.
This is stated up front so the verdict is not mistaken for a test of *all* microstructure: it is a test of
the microstructure that is actually obtainable.

## Evaluation contract (carried from prior phases + microstructure-specific)

- **Per-symbol** BTC/ETH/SOL (never pooled).
- **Cost-adjusted**: round-trip 0.30% = 2×(0.001 fee + 0.0005 slippage), unchanged. (Note: a high bar for
  short-horizon 5m signals — intentionally honest.)
- **Walk-forward**: 4 sequential folds; an effect must hold its sign across folds.
- **Cross-symbol**: an edge must generalise across all three majors.
- **Information content (cost-free)**: Spearman IC of each microstructure feature vs forward return /
  forward |return|, reported alongside the OHLCV-momentum IC to show whether microstructure adds
  *incremental* information beyond OHLCV.
- **Regime-aware, not OHLCV-driven entry**: liquidity regime (microstructure-derived) gates the flow
  signal; OHLCV is contextual only.

Signal designs → `orderflow_signal_design.md`, `liquidity_microstructure_analysis.md`. Results →
`microstructure_walkforward_results.md`. Verdict → `phase17_final_verdict.md`.
