# Phase 20 — Consolidated Edge Synthesis

**Date:** 2026-06-13. Final synthesis across the entire program (Phases 5–19). Documentation only — no
strategy/parameter/threshold/risk/execution change; no profitability claimed. This is the master ledger
of *everything tested for edge* and where each landed.

## The single number

**READY = 0.** No signal — OHLCV, derivatives data, microstructure, cross-venue, or any combination —
produced a positive, cost-adjusted, walk-forward-stable, cross-symbol expectancy. Suite state unchanged:
**READY 0 / NEEDS_IMPROVEMENT 1 / INCONCLUSIVE 4 / INVALIDATED 5 / RETIRED 2 (slots empty).**

## Master edge ledger — every domain tested, best result, why not deployable

| Domain | Phase | Best observed | Class | Why not deployable |
|---|---|---|---|---|
| OHLCV strategies (12) | 5–11, deploy/arch | none cost-positive | INVALIDATED/INCONCLUSIVE | edgeless net of cost across TF/regime/symbol |
| Correct deployment (design-TF/regime/per-symbol) | deploy-valid | 0/30 cells | — | READY=0 *survives* correct deployment |
| Replacement candidates (STR, DCB) | replacement | stable-negative | INVALIDATED | WFO 0–1/4; same edgeless pattern |
| Symbol universe (11–12 symbols) | 12 | only episodic XRP | — | READY=0 is strategy-wide, not a major-coin artifact |
| Long history (7–9 yr) | 15 | XRP/DOGE/LINK positives collapse | — | coverage is **not** the cause; 1yr ≡ multi-yr |
| Open interest (oi_footprint) | pre-13 | — | NO_GO | DIRECTIONAL_NO_GO; OI history ~30d cap → untestable |
| **Funding rates** | 14 | extreme-neg→BTC/ETH bounce | **WEAK** | mostly NO_INFORMATION; the one thread fails SOL + WFO-unstable |
| **Microstructure order flow / CVD** | 17 | flow IC ≈ −0.03 | **NO_EDGE** | 58% OHLCV-redundant, weaker than OHLCV; gross edge ≈ 0 |
| Microstructure liquidity (trade-intensity) | 17 | vol IC ≈ +0.13 | NO_EDGE | real but redundant w/ OHLCV vol; non-directional |
| **Cross-exchange catch-up (Binance→MEXC)** | 18 | **dispersion IC ≈ +0.10** | **WEAK_EDGE** | strongest real non-OHLCV signal, but sub-spread/sub-cost → latency-arb, 0/4 folds |
| Perp-spot lead-lag / basis | 18 | perp leads spot (k1≈0.02) | WEAK_EDGE | real, cross-symbol, but sub-cost |
| Cross-asset lead-lag (BTC→ETH/SOL) | 18 | lead ≈ 0.01–0.02 | NO_EDGE | co-move is contemporaneous/OHLCV-visible; lead ambiguous |
| **Funding × microstructure combined** | 19 | BTC/ETH +0.40–0.64% @72h | **WEAK_EDGE** | reproduces Ph14 thread; fails SOL; fold-fragile; flow doesn't beat funding-only |
| L2 order-book depth | 13/17 | — | UNTESTABLE | no integrated historical source (backtest-blocked) |
| Liquidations | 13/17 | — | UNTESTABLE | public backfill removed (backtest-blocked) |
| Sub-minute / HFT lead-lag | 18 | — | OUT OF REACH | below 1m resolution; needs co-located execution |

## The two "best" findings — and why neither is an edge

The program surfaced exactly two signals worth naming. Both are **real and cross-symbol-consistent
*information*; neither is a *deployable edge*:**

1. **Cross-exchange catch-up (Phase 18)** — Binance leads MEXC; dispersion predicts MEXC's next move,
   IC ≈ +0.10. The single strongest, genuinely non-OHLCV signal in the program. **Not deployable:** the
   dispersion (~0.01–0.025%) is smaller than spread + 0.30% cost; it is a **latency-arbitrage** effect
   inside the cost barrier, requiring co-located sub-minute execution this system does not have. 0/4 folds.

2. **Funding capitulation on BTC/ETH (Phases 14, 19)** — extreme-negative funding (+ capitulation selling)
   → +0.40–0.64% net @72h on BTC/ETH. **Not deployable:** fails SOL (−1.15%), walk-forward-fragile (means
   driven by 1–2 early folds), and microstructure confirmation does not improve it.

**The recurring pattern across all weak findings:** information that is either (a) redundant with OHLCV,
(b) too small to clear realistic cost, (c) inside the spread (latency-arb), or (d) cross-symbol-
inconsistent and fold-fragile. None clears the bar a deployable edge requires.

## What the search has and has not covered (honest boundary)

- **Exhaustively covered (no deployable edge found):** all 12 OHLCV strategies + 2 replacements; design-TF/
  regime/per-symbol deployment; 11–12 symbol universe; 7–9 year history; funding (3yr×24sym); open
  interest; microstructure order flow / CVD / liquidity; cross-exchange & cross-asset & perp-spot lead-lag;
  funding × microstructure combinations.
- **Backtest-blocked / out of reach (not ruled out, but not obtainable here):** L2 order-book depth and
  historical liquidations (no integrated history); sub-minute/HFT lead-lag (below resolution + needs
  co-located execution). The cross-exchange catch-up (Ph18) is evidence that *real* microstructure edge
  exists at the HFT scale — it is simply not capturable by this system.

## Conclusion

Every edge hypothesis reachable with integrated data and retail-grade execution has been tested. The
deployable-edge search space is **exhausted**: the result is consistently **no cost-surviving,
cross-symbol, walk-forward-stable edge**, with two real-but-undeployable information threads (cross-
exchange catch-up; funding capitulation) marking the frontier. Termination rationale and final disposition
→ `program_termination.md`; one-page verdict → `final_phase20_verdict.md`.
