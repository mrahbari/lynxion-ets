# E13 — XS-COMBO per-leg risk, post-fix live trades, false "POSITION CLOSED" alerts (2026-11-23)

## 1. XS-COMBO: can each leg follow the platform's bounded-loss rule?
Trigger: 2026-11-22 AKEUSDT closed at -147 USDT (-30 % of a 500 USDT leg) under the 50 % disaster stop.
That leg size came from the first rebalance (book 20,000 / 40 names = 500); the book was then cut to the
.env cap (3,200 gross, about 80 per name, max loss at the 50 % stop about 40 USDT per leg).

Script `research/v2/experiments/e13_xs_combo_risk_sizing.py`, rules pre-registered in its docstring.
CSV `E13_xs_combo_risk_sizing.csv`.

| variant | DEV SR | DEV maxDD | DEV worst leg (% book) | HOLD SR | HOLD maxDD |
|---|---|---|---|---|---|
| EW, no stop | 2.02 | -13.6 % | 8.79 | 1.67 | -11.9 % |
| **EW, 50 % stop (live)** | **2.11** | -14.4 % | 4.17 | **1.72** | -12.0 % |
| EW, 20 % stop | 0.58 | -35.3 % | 1.68 | 0.57 | -17.7 % |
| equal-risk, 50 % stop | 2.19 | -12.1 % | 3.81 | 1.41 | -13.1 % |
| equal-risk, stop 2 sigma*sqrt(7) | 1.60 | -20.6 % | 2.58 | 1.65 | -8.2 % |
| equal-risk, stop 3 sigma*sqrt(7) | 1.95 | -15.7 % | 2.83 | 1.66 | -10.9 % |
| equal-risk, stop 4 sigma*sqrt(7) | 2.09 | -11.9 % | 3.50 | 1.53 | -12.6 % |

Decision rule (SR >= 0.9 x live AND worst leg <= 0.5 x live, on DEV): **no variant passes**. A
per-position stop near the platform's 1-3 % rule would destroy the carry edge (20 % already cuts SR to
0.58). Live stays unchanged. XS-COMBO's risk unit is the book (worst week about 5-7 % of gross), not
the single leg; the per-leg cap is set by the book size (gross / 40 x 50 %).

## 2. Post-fix platform trades (entries since 2026-11-22 21:00 UTC, journal)
17 closed trades, +8.0 USDT net (fees 1.4), 11 SL / 6 TP; SL exits average -0.97 R (worst -1.5 R,
PROMUSDT gap), TP exits +1.8 R.

| strategy | n | PnL | mean R | SL/TP | E9 backtest mean R |
|---|---|---|---|---|---|
| VWAPReversal | 7 | +18.8 | +0.78 | 3/4 | -0.11 |
| OIFootprint | 7 | -16.9 | -1.04 | 7/0 | -0.11 |
| TrendFollow | 2 | +2.5 | +0.21 | 1/1 | -0.06 |
| MeanReversion | 1 | +3.6 | +1.49 | 0/1 | -0.06 |

Four of the seven OIFootprint losses are two A-B-A re-entry pairs (ELSAUSDT 08:38/08:42 UTC,
PROMUSDT 10:22/10:24), both before the entry-hold fix went live (runner restart 10:54 UTC). n = 17 is far
too small to tune on: VWAP +0.78 R over 7 trades vs -0.11 R over 13,763 backtest trades is consistent
with luck. These trades are used for live-vs-backtest parity (stop R, TP R, duration), not for fitting.

## 3. False "EXCHANGE POSITION CLOSED — UNKNOWN" alerts (incident, fixed)
12:42 and 13:31 local: all 12 platform positions were booked closed with outcome UNKNOWN, a 60 min safety
cooldown each and a Telegram alert, while they were still open on BingX with their SL/TP orders (read-only
check). Cause: BingX VST answers `/openApi/swap/v2/user/positions` intermittently with code 0 and an
**empty list** (probe: 7 empty replies in ~14 s, then the full 51; a later 4-minute probe saw none).
The adapter correctly raises on error codes, but an empty list with code 0 looks like a flat account.
The 12:18 "ENTRY HELD" for OKB/DOT/ONDO was the same blip; the entry hold prevented duplicates.

Fix (`infrastructure/execution/broker_reconciliation.py`, commit 704c73c): a closure is booked only after
the symbol is absent on 2 consecutive passes (3 when every absent pass saw an empty snapshot). Pending
symbols stay in the active set, so same-symbol entries stay held. Cost: a real exit is booked 60-120 s
later. The UNKNOWN alert now says the closing order was not found and the position should be checked
on BingX. Tests: `tests/unit/test_unreconciled_exit_entry_hold.py`.

Not fixed (backlog): other consumers of the positions endpoint (exposure / max-position checks,
`get_position` duplicate guard) can still see a blip as flat for one call.
