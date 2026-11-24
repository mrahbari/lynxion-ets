# E28 — six setups with their designed SL/TP instead of the global clamp (2026-11-24)

Pre-registered and committed before the run (research/v2/experiments/e28_designed_levels.py). Same designs,
engine, universe, windows and costs; the level sanitiser kept safety checks only (correct side, stop <= 15 %,
target <= 30 %).

| design | clamped net R DEV / HOLD (bp) | designed net R DEV / HOLD (bp) | median stop designed | decision |
|---|---|---|---|---|
| TF1 TrendFollow (live) | -0.027 / -0.010 (-8.3 / +2.6) | -0.036 / -0.048 (-8.5 / -5.0) | 1.96 % | keep clamp |
| VR1 VWAPReversal (live) | -0.017 / -0.062 (-3.3 / -9.1) | -0.164 / -0.215 (-10.1 / -13.5) | 0.74 % | keep clamp |
| MR1 Connors RSI(2) | -0.034 / -0.146 | -0.047 / -0.086 | 2.47 % | keep clamp |
| BO1 TTM squeeze | -0.137 / -0.174 | -0.314 / -0.285 | 0.61 % | keep clamp |
| LQ1 pivot sweep | -0.138 / -0.090 | -0.291 / -0.305 | 0.62 % | keep clamp |
| BRK_RETEST (E27) | -0.147 / +0.026 | -0.210 / -0.098 | 1.10 % | keep clamp |

**Result: the clamp is not the problem — it helps.** With their designed (tighter) stops every setup is worse,
also in bp per trade (not only in R units): stops of 0.5-0.8 % are inside the noise and the ~14 bp round-trip
cost is 0.2-0.3 R. The 1.2 % stop floor acts as a cost/noise filter. No setup has an edge with either levels.
Keep `sanitize_sltp_levels` as is; no live change.
