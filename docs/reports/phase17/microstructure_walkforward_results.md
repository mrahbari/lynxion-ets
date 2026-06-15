# Phase 17 — Microstructure Walk-Forward Results (consolidated)

**Date:** 2026-06-13. Analysis only; no profitability claim. Consolidated cost-adjusted, walk-forward,
per-symbol, cross-symbol results for every microstructure signal. Data: futures 5m, BTC/ETH/SOL,
2024-06 → 2026-06 (~213k bars/symbol). Cost = 0.30% round-trip (unchanged). Horizon = 6 bars (30 min).
4 sequential folds (~6 months each). Raw: `phase17_results.json`.

## Cost-adjusted expectancy & walk-forward (all directional signals)

| Signal family | BTC | ETH | SOL | folds positive (each symbol) | cross-symbol |
|---|---:|---:|---:|:--:|:--:|
| A. flow-follow | −0.305% | −0.304% | −0.306% | 0/4 | all-negative |
| A. flow-contrarian | −0.295% | −0.296% | −0.294% | 0/4 | all-negative |
| B. flow \| liquidity-expansion | −0.309% | −0.305% | −0.303% | 0/4 | all-negative |
| B. flow \| liquidity-contraction | −0.303% | −0.304% | −0.307% | 0/4 | all-negative |

- **Every directional microstructure signal is negative net of cost on every symbol, with 0/4
  walk-forward folds positive.** Net ≈ −(cost), so **gross directional edge ≈ 0** — there is no real edge
  being eroded by cost; there is essentially no gross edge.
- **Cross-symbol:** uniformly negative — no symbol carries a flow edge the others lack.
- **Walk-forward:** not a single signal × symbol is sign-stable positive across folds.

## Information-content summary (cost-free, Spearman IC)

| Relationship | BTC | ETH | SOL | vs OHLCV baseline | verdict |
|---|---:|---:|---:|---|---|
| flow_k → forward return (direction) | −0.032 | −0.029 | −0.026 | weaker than OHLCV (−0.045) & 58% correlated | **redundant, no incremental info** |
| intensity_z → forward \|return\| (volatility) | +0.139 | +0.136 | +0.122 | weaker than OHLCV (+0.214) | **real but redundant, non-directional** |
| intensity_z → forward return (direction) | +0.004 | +0.004 | −0.001 | ~0 | **no info** |
| funding(extreme-neg) × sell-flow → forward return | +0.011% | +0.010% | +0.011% | n/a | **cross-symbol consistent but ~37× below cost** |

## Stability across time windows

- The directional signals' fold expectancies are all-negative on every symbol (no positive fold to
  stabilise around) — see `phase17_results.json` `wfo.fold_exp`.
- The two *informative* relationships (flow→reversal, liquidity→volatility) are sign-stable across
  symbols, i.e. the **information is stable** — it is simply (a) redundant with OHLCV and (b) too small
  and/or non-directional to convert into cost-surviving expectancy.

## Cross-symbol robustness

Robust in the *negative* direction: BTC, ETH, SOL agree on every count — no edge, redundant information,
sub-cost interaction. The result is not a single-symbol artifact.

## Bottom line for the verdict

- **Deployable edge:** none — 0/4 folds, all-negative net of cost, all symbols, all families.
- **Incremental information beyond OHLCV:** none for direction (flow is a weaker, 58%-redundant proxy for
  OHLCV short-term reversal); none usable for volatility (liquidity is real but weaker/redundant and
  non-directional).
- **Caveat:** L2 order-book depth and historical liquidations were **backtest-blocked** (no integrated
  history), so this verdict covers order flow + trade-structure liquidity + funding×flow — not the entire
  microstructure space. Classification & replacement decision → `phase17_final_verdict.md`.
