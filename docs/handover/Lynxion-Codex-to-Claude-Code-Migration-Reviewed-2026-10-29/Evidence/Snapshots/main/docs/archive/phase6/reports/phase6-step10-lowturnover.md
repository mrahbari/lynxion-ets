# Phase 6 · Step 10 — Lower-Turnover / Longer-Hold Rescue Test (revert_highvol_3)

_Does holding longer / trading only high-conviction extremes flip the lead net-of-cost positive? Non-overlapping entries (1 round-trip per hold), 24-symbol 8h universe, round-trip cost 10 bps. Hold in 8h bars (1=8h,3=1d,9=3d,21=7d). Signal-decoupled; no SL/TP/sim._

| conviction-only | hold | trades | gross bps | net @10bps | win% | t(net) | robust? |
|:--:|---:|---:|---:|---:|---:|---:|:--:|
| False | 1 | 34,900 | +6.4 | -3.6 | 53 | -2.3 | no |
| False | 3 | 12,226 | +0.3 | -9.7 | 52 | -2.2 | no |
| False | 9 | 4,568 | -8.7 | -18.7 | 51 | -1.5 | no |
| False | 21 | 2,259 | -102.7 | -112.7 | 49 | -4.2 | no |
| True | 1 | 308 | +41.3 | +31.3 | 59 | +1.5 | no |
| True | 3 | 147 | +52.9 | +42.9 | 56 | +0.9 | no |
| True | 9 | 73 | +101.0 | +91.0 | 60 | +0.8 | no |
| True | 21 | 40 | +513.1 | +503.1 | 60 | +2.0 | no |

_Robust = net>0 AND ≥500 trades AND t(net)≥2 — guards against the small-sample/outlier mirage._

❌ **Lower turnover does NOT rescue it.** The statistically meaningful rows (conviction-off, thousands of trades) are net-NEGATIVE and get WORSE as hold grows — short-horizon reversion front-loads and decays, so longer holds add variance without proportional gross. The eye-catching conviction-only positives (e.g. +500 bps) are a **small-sample mirage**: 40–308 trades, low/insignificant t(net), and a gross that explodes with hold — classic outlier domination, not edge. No robust net-positive configuration exists. **revert_highvol_3 is not tradeable on free OHLCV at any tested turnover.**

_No tuning beyond the pre-stated hold/conviction grid. The conviction-only cells are reported but explicitly flagged as not statistically reliable._
