# E21 — canonical, cost-aware rebuild of the live setups (E16-U10), 2026-11-24

Same E9 engine/universe/costs (10 liquid USDT-M perps; DEV 2025-11..2026-06, HOLDOUT 2026-07..10).
Rule pre-registered and committed before the run: mean net R >= +0.05 with n >= 100 on DEV and > 0 on HOLDOUT.

| design | window | trades | mean R | PF | symbols + |
|---|---|---|---|---|---|
| baseline trend_following (E9, live) | DEV / HOLDOUT | 1839 / 838 | -0.028 / -0.055 | 0.96 / 0.93 | |
| TF1 Donchian-20 + EMA50>200, 2 ATR stop, 1h | DEV / HOLDOUT | 1235 / 583 | -0.027 / -0.010 | 0.94 / 1.02 | 4/10, 5/10 |
| TF2 same on 4h | DEV / HOLDOUT | 453 / 200 | -0.056 / +0.010 | 0.92 / 1.03 | 3/10, 4/10 |
| baseline vwap_reversal (E9, live) | DEV / HOLDOUT | 8997 / 3877 | -0.124 / -0.123 | 0.82 / 0.83 | |
| VR1 session VWAP 2-sigma re-entry, 15m, cost filter | DEV / HOLDOUT | 3351 / 1575 | -0.017 / -0.062 | 0.96 / 0.89 | 2/10, 3/10 |

**Result: all FAIL.** Canonical, cost-aware definitions cut losses (VWAP from -0.12 R to about -0.02/-0.06 R)
but none has positive net edge. Consistent with E9: single-asset technical setups on liquid perps carry
~0 gross edge at these horizons; costs make them negative.

**Decision.** Pre-registered rule says retire both live strategies (baselines negative on HOLDOUT). That
would leave no platform strategy trading on VST, so it is put to the operator (critical) instead of
applied silently. No live change made.
