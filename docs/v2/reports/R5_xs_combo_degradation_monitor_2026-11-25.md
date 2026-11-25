# R5 — XS-COMBO-V1 degradation monitor (2026-11-25)

Goal: detect when the only research-supported edge (cross-sectional funding carry, XS-COMBO-V1) weakens, gets
too expensive to run, or drifts from its design. Doing so must not change the strategy. The monitor is
**observational**: it never places, cancels or sizes orders, and never changes the schedule or parameters.

## What was there before

- `research/v2/live/tracking.py`: a daily shadow-funding ledger (VST pays no funding) at BingX and Binance
  rates (`data/v2_live/tracking.csv`).
- `equity.csv`: account-wide equity, shared with the platform sleeve, so it cannot measure the sleeve alone.
- `orders.jsonl`: order ledger with the plan notional and the VST fill `avgPrice`.
- `targets/<date>.json`: target weights per rebalance.
- No thresholds and no degradation indicators. Live history is short: one rebalance (2026-11-22) and 3 tracking days.

## Implementation (no new architecture)

| File | Change |
|---|---|
| `research/v2/live/monitor.py` | New module. Reads the existing files, writes `data/v2_live/monitor.csv` (one row per day) and `monitor_state.json` (yesterday's book snapshot for daily P&L) |
| `research/v2/live/rebalancer.py` | One guarded call at the end of the daily job, after rebalance and stops. Errors are logged as `monitor_error` and never stop the job. Its lines are appended to the existing daily Telegram report |
| `research/v2/experiments/e38_xs_combo_monitor_baseline.py` | Thresholds + walk-forward validation (pre-registered, commit before the run) |
| `research/v2/results/xs_combo_monitor_thresholds.json` | Thresholds used live |
| `research/v2/tests/test_monitor.py` | 7 tests: threshold sides, carry sign, concentration, turnover, slippage/failure parsing, the 28-day minimum, read-only daily P&L, ALERT → review text |

## Indicators and thresholds

Thresholds come from the frozen backtest's own distribution, 2020-01..2026-10, live-like universe.
- **Rule:** WARN at p10 and ALERT at p2.5 on the bad side.
- **Exception, slippage:** WARN above the backtest cost model, ALERT above 2× it. 2× is the cost stress already passed in E2–E4.

| Indicator | Definition (same in backtest and live) | Median | WARN | ALERT | Status type |
|---|---|---|---|---|---|
| ex_ante_carry | −Σ w·(21-day funding)·365/21 of the target book | +14.5 %/yr | ≤ +4.6 % | ≤ 0 | alarm (leading in principle) |
| adverse_share | share of target names whose funding works against them | 24 % | ≥ 47 % | ≥ 51 % | alarm |
| realized_carry | 28-day shadow funding (Binance rates) / gross, annualised | +10.9 %/yr (holdout +34 %) | ≤ +5.3 % | ≤ +3.5 % | alarm, needs 28 live days |
| turnover | Σ\|Δw\| per rebalance | 0.81 | ≥ 1.01 | ≥ 1.10 | alarm |
| slippage_bp | fill vs plan price, adverse positive, per rebalance | — | > 6.3 bp | > 12.6 bp | alarm |
| max_share / top5_share | position share of gross, drifted | 2.3 % / 10.4 % | 4.7 % / 16.5 % | 7.9 % / 36.8 % | alarm |
| abs_net_exposure | \|long − short\| / gross | 0.7 % | 3.1 % | 5.0 % | alarm |
| fail_rate, overdue_days | failed orders at last rebalance; days since rebalance | — | any / ≥ 8 d | — / ≥ 9 d | operational rule |
| ret_56d, drawdown, abs_beta_btc | 8-week return, DD from peak, 28-day beta | +25.8 %/yr, −3.1 %, 0.06 | p10 shown | p2.5 shown | **INFO only** (failed validation) |

## Validation (E38, pre-registered)

Thresholds were fit on 2020–2022 and applied out-of-sample to 2023-01..2026-10 (1,400 days).
Raw data: `E38_monitor_validation.csv`.

| Indicator | OOS ALERT rate | Usable alarm (≤ 10 %) | Leading? (next-28-day return after WARN) |
|---|---|---|---|
| ex_ante_carry | 0.0 % | yes | not testable: no WARN week out-of-sample |
| adverse_share | 0.0 % | yes | — |
| realized_carry | 4.6 % | yes | no (t −0.63) |
| max_share / top5 / net exposure | 0.1 % / 0 % / 1.6 % | yes | — |
| ret_56d | 11.5 % | **no** | **no — opposite**: returns were higher after WARN (t +2.14) |
| drawdown | 21.8 % | **no** | — |
| abs_beta_btc | 18.6 % | **no** | — |

What this means:
- **Carry, structure and execution indicators are stable alarms.** They show whether the book still has the
  properties the edge depends on.
- **No indicator predicts weaker future returns.** None is called "leading".
- **Weak recent performance is followed by recovery, not further decay** (t +2.14). Cutting or pausing the strategy
  after a drawdown would have hurt. The monitor therefore shows performance indicators as INFO and never proposes an
  intervention on them alone.

## Robustness finding: rebalance-phase sensitivity (material)

Replaying the frozen strategy with the weekly rebalance on each of the 7 possible weekdays gives very different holdout results:

| Universe | 2020–24 net Sharpe by phase | 2025–26 net Sharpe by phase |
|---|---|---|
| all symbols | 1.61 – 2.11 | 0.85 – 2.07 |
| live-like (non-perpetual excluded) | 1.64 – 2.11 | **0.50 – 1.77** (annual +13 % … +43 %) |

- The published holdout Sharpe of 1.39 is one draw from this range.
- The live phase (rebalancing every 7 days from 2026-11-22) is another draw.
- Expectations for live should use the range, not the single number.
- This dispersion is also the noise floor for R6b: any timing benefit must be measured paired within each phase.

## First live reading (2026-11-25)

Run read-only on a copy of `data/v2_live`.

| Indicator | Value |
|---|---|
| ex-ante carry | +81 %/yr [OK] |
| adverse names | 8 % [OK] |
| concentration max / top5 / net | 3.5 % / 15.3 % / 1.5 % [OK] |
| slippage | +5.1 bp [OK] |
| failed orders | 0 of 78 |
| BingX/Binance funding ratio | 0.91 |
| realized carry | NA, 3 of 28 days |

The first real run will be the daily job (LaunchAgent, 02:15 local).

## Limits

- **VST fills are simulated.** The plan price is the BingX mainnet price at plan time, so slippage mixes VST-vs-mainnet basis with execution cost.
- **No funding settles on VST.** Carry is the shadow ledger; positions are assumed held over the whole window.
- **Daily P&L approximation.** It uses yesterday's book × price change + shadow funding. A stop-out during the day is valued at the run-time price.
- **Ex-ante carry is not a forecast.** It uses trailing 21-day funding; out-of-sample it never reached WARN, so its lead value is untested.
- **Backtest vs live differences.** Thresholds come from Binance data with no stops; live has 50 % SL / 40 % TP and BingX symbols.
- **Statistical power.** The realized-carry alarm needs 28 days; 8-week evidence arrives ~2027-01-20, after the VST deadline (~2026-12-22).
- **Correlation / beta** is reported as INFO only.

## Interventions

**None proposed now; all indicators are OK.**

A WARN or ALERT line names the indicator, the value, the backtest band and a review proposal for the operator. Nothing is executed automatically.

## R6b

Pre-registered as E39 (`research/v2/experiments/e39_reversal_timed_rebalance.py`, mechanics self-check only). Not run; no live change.
