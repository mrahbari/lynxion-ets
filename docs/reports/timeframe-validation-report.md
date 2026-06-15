# Timeframe Validation Report

**Date:** 2026-06-12. Full validation of the 12 production strategies on the
re-architected timeframes — **BTC/ETH/SOL × {15m, 30m, 1h} × {90, 180, 365d}**, existing
production parameters only (no tuning/optimization/threshold change). Methodology:
`timeframe-refactor-report.md`. Matrices: `eval_matrix_{15m,30m,1h}.json`.

**Coverage:** 15m = 108/108 · 30m = 108/108 · 1h = 108/108 — **all complete.**

## Aggregate results per timeframe

| TF | ok cells | significant (≥30 trades) | **positive significant** | avg win-rate | Σ PnL | GO verdicts |
|----|----|----|----|----|----|----|
| **15m** | 83 | 42 | **0** | 23.9% | **−28 574** | 0 |
| **30m** | 84 | 39 | **1** | 23.1% | **−22 690** | 1 |
| **1h** | 73 | 33 | **7** | 19.9% | **−16 877** | 6 |

The cost gradient is monotonic and decisive: positive-significant-cell count rises with
timeframe (15m 0 → 30m 1 → 1h 7) and aggregate loss shrinks (−28.6k → −22.7k → −16.9k),
exactly as the cost-cliff predicts — yet **all three horizons remain net-negative.** The
single 30m positive cell (ETH 365d scalping +8.7, 36 trades) is marginal and isolated.

### Reading the table
- **Every timeframe is net-negative in aggregate.** No horizon makes the suite profitable.
- **15m — the mandated "primary signal timeframe" — has ZERO positive significant cells**
  and the worst aggregate PnL. It sits on the ~15m cost-breakeven cliff (TP ≈ 0.57% vs
  0.30% cost), so its thin margin is consumed by costs despite a 23.9% win rate.
- **1h is the least-bad horizon** (7 positive significant cells, 6 GO) — the most
  cost-robust — but still net-negative and with no cross-symbol stability (see
  `cross-symbol-stability-report.md`).
- Win rates (19–24%) are far below the ~40% breakeven for RR 1.5:1 → structural
  unprofitability with this geometry, regardless of timeframe.

## The 7 positive significant cells (all at 1h)
| symbol | window | strategy | PnL | trades | win | verdict |
|---|---|---|---|---|---|---|
| ETH | 365d | oi_footprint | +165 | 89 | 0.235 | GO |
| BTC | 180d | mtf_trend | +156 | 88 | 0.237 | GO |
| BTC | 180d | momentum | +173 | 57 | 0.216 | INSUFFICIENT_DATA |
| BTC | 90d | mtf_trend | +132 | 30 | 0.262 | INSUFFICIENT_DATA |
| ETH | 90d | scalping | +61 | 33 | 0.246 | INSUFFICIENT_DATA |
| ETH | 365d | trend_following | +50 | 66 | 0.211 | GO |
| ETH | 180d | oi_footprint | +28 | 41 | 0.229 | INSUFFICIENT_DATA |

These are **isolated, single-symbol** positives. Each strategy is heavily negative on the
other symbols (esp. SOL), so none represents a transferable edge. (`oi_footprint`'s +165
also rests on a volume-based OI proxy — data-blocked.)

## Per-strategy validation summary

| strategy | trades (all TF) | best cell | profitable? | verdict |
|---|---|---|---|---|
| mtf_trend | 3 579 | BTC 1h +156 (GO) | no (BTC-only) | NEEDS_IMPROVEMENT |
| oi_footprint | 2 284 | ETH 1h +165 (GO) | no (ETH-only; data-blocked) | NEEDS_IMPROVEMENT |
| momentum | 1 628 | BTC 1h +173 | no (BTC-only) | NEEDS_IMPROVEMENT |
| trend_following | 1 436 | ETH 1h +50 (GO) | no | NEEDS_IMPROVEMENT |
| scalping | 1 356 | ETH 90d +61 | no (neg every other cell) | NON_VIABLE |
| liquidity | 303 | ETH +58 | no | NEEDS_IMPROVEMENT |
| volatility_breakout | 172 | — | no | NEEDS_IMPROVEMENT |
| sweep_scalper | 116 | SOL 1h +34 | no | NEEDS_IMPROVEMENT |
| vwap_reversal | 7 | — | no (barely trades @≥15m) | NEEDS_IMPROVEMENT |
| mean_reversion | 2 | — | no (barely trades) | NEEDS_IMPROVEMENT |
| breakout / crypto_breakout | 0 | — | no (Type-B confidence gate) | NEEDS_IMPROVEMENT |

## Conclusion
Validation across 15m/30m/1h confirms the rehabilitation finding on cost-viable
timeframes: **the strategies are correct and measurable but not profitable, and none is
stable across symbols or horizons.** 15m (primary signal TF per the mandate) is the worst
performer (cost-cliff); 1h is the most robust but still edgeless in aggregate. **READY 0 ·
NEEDS_IMPROVEMENT 11 · NON_VIABLE 1.** See `final-deployment-readiness-report.md` for the
deployment decision and `production-candidate-ranking.md` for prioritized next steps.

_All three matrices (15m/30m/1h × BTC/ETH/SOL × 90/180/365d = 324 cells) are complete.
The 30m result (1/39 positive significant, −22.7k) confirms the monotonic cost gradient
and does not alter any verdict._
