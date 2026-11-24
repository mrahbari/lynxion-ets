# E26 — TrendFollow exit: live (2 ATR / 6 ATR / BE-trail) vs Turtle 10-bar exit (2026-11-24)

Pre-registered and committed before the run (research/v2/experiments/e26_trend_turtle_exit.py). Same live
entry in both arms; E9 universe, windows and costs. Arm A reproduces E21 TF1 (sanity: -0.019 / -0.006 vs
-0.027 / -0.010).

| arm | window | n | net R | win | PF | max R | symbols + |
|---|---|---|---|---|---|---|---|
| A live | DEV | 1165 | -0.019 | 0.405 | 0.95 | 3.0 | 4/10 |
| A live | HOLDOUT | 568 | -0.006 | 0.424 | 1.00 | 3.0 | 4/10 |
| B Turtle | DEV | 1006 | **-0.113** | 0.259 | 0.78 | 20.7 | 1/10 |
| B Turtle | HOLDOUT | 451 | **+0.133** | 0.313 | 1.21 | 28.2 | 8/10 |

**Result: KEEP the live exit; no edge.** The Turtle exit lets winners run (max 20-28 R) and is strongly positive
on HOLDOUT, but clearly negative on DEV: its result depends on whether the period trends, not a stable edge.
Not adopted (pre-registered rule needs better on both windows). Worth re-testing only with a trend-regime
condition defined in advance — not tuned on these windows.
