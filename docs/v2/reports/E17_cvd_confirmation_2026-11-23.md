# E17 — CVD as the entry confirmation of the platform strategies (roadmap E13-1, 2026-11-23)

Script `research/v2/experiments/e17_cvd_confirmation.py` (pre-registered, committed before running: edc2492);
data `e17_cvd_data.py` (Binance 5m klines with taker-buy volume, 10 symbols, Oct 2025 - Oct 2026).
E9 trades: 28,561 DEV / 12,588 holdout. CVD = aggressive buy minus sell quote volume over the last 5 / 15 /
60 min of closed bars before entry. "confirm" = CVD sign agrees with the trade side (the live rule).

Pooled lift of trades in each state vs the strategy's own mean (R):

| window | DEV confirm | t | HOLD confirm | t |
|---|---|---|---|---|
| 5 min (live rule) | -0.003 | -0.30 | -0.004 | -0.25 |
| 15 min | +0.002 | 0.21 | -0.001 | -0.09 |
| 60 min | +0.008 | 0.78 | -0.005 | -0.34 |

Strategy x window x state cells: **0 of 48 pass DEV**. CVD confirms about half of the trades (48-52 %),
and confirmed trades are neither better nor worse.

**Verdict: FAIL.** CVD carries no information about the outcome of these strategies' trades. Enabling the
OBI/CVD confirmation fail-closed (E14-3) would cut roughly half to two thirds of the entries (live shadow so
far: 13 CONFIRM / 29 WOULD_BLOCK / 5 no data, distinct intents) without improving them.

Decision: do not enable E14-3 on CVD grounds. OBI cannot be tested offline (no historical book); the live
shadow log keeps collecting OBI/CVD verdicts for a week and is matched with trade outcomes (E14-2) before
the final E14-3 decision. Expected outcome given E11/E12/E14/E17: no edge; then the confirmation stage stays
in shadow (or off) permanently.
