# E15 — XS-COMBO rank as a filter for single-symbol strategies (roadmap E9-2, 2026-11-23)

Script `research/v2/experiments/e15_xs_rank_filter.py` (pre-registered, committed before running: 5649596).
E9 trades (28,561 DEV / 12,588 holdout), each tagged with the symbol's frozen XS-COMBO-V1 percentile rank
(all 10 symbols matched 100 %). States vs trade side: aligned / opposed (rank 0.5), extreme_aligned (top or
bottom 20 %).

Pooled lift vs each strategy's own mean (R):

| state | DEV n | DEV lift | t | HOLD n | HOLD lift | t |
|---|---|---|---|---|---|---|
| aligned | 14,131 | **+0.084** | 7.97 | 6,123 | **-0.024** | -1.55 |
| opposed | 14,430 | -0.082 | -8.16 | 6,465 | +0.023 | 1.49 |
| extreme_aligned | 7,196 | **+0.115** | 7.75 | 2,109 | **-0.036** | -1.34 |

Per strategy x state: 1 DEV pass of 32 (volatility_breakout extreme_aligned: n 256, +0.19 R, PF 1.37);
holdout fails (n 72, -0.21 R, PF 0.70).

**Verdict: FAIL.** A strong, consistent DEV effect (all 8 strategies better when aligned) that reverses sign
in the holdout. This is the regime-dependence pattern (the composite contains a 7-day taker-buying term that
behaves like short-term flow momentum, which worked in Nov 2025-Jun 2026 and not after), not a stable edge.
Not deployed. Note: the rank was used one day later than needed (available D + 25 h; row D is known at D),
a conservative choice fixed before running and not changed afterwards.
