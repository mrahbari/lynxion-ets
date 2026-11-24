# E25 — canonical MeanReversion / Breakout / Liquidity (2026-11-24)

Pre-registered and committed before the run (research/v2/experiments/e25_canonical_rest.py). E9 engine, 10 liquid
perps, live-equivalent execution and costs (the live SL/TP sanitiser applies: minimum stop distance 1.2 %).

| design | DEV n / net R | HOLDOUT n / net R | baseline (live def.) DEV / HOLDOUT | edge | adopt |
|---|---|---|---|---|---|
| MR1 Connors RSI(2), 1h | 1380 / -0.034 | 651 / -0.146 | -0.087 / -0.014 | FAIL | no (worse on HOLDOUT) |
| BO1 TTM squeeze release, 15m | 1921 / -0.137 | 897 / -0.174 | -0.137 / -0.124 | FAIL | no |
| LQ1 pivot sweep + MSS, 15m | 6219 / -0.138 | 2654 / -0.090 | -0.092 / -0.120 | FAIL | no (worse on DEV) |

**Result.** No textbook variant has an edge and none beats its current definition on both windows, so by the
pre-registered rule the current definitions stay (MeanReversion, Breakout, Liquidity are not live). 0-2 of 10
symbols positive in every cell: the losses are broad, not symbol-specific.
**Strategy-layer reading.** Canonical rebuilds helped where the old definition was clearly broken (VWAP, Trend:
E21, adopted). For these three the old and the canonical versions are equally without edge; further work on
single-asset intraday price setups has very low expected value (E9-E25, ~35 Codex candidates).
