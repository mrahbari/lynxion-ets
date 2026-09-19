# Lead B — Quarter-hour flow economic holdout preregistration

**Frozen:** 2026-09-19, before opening Lead-B outcomes from 2026

**Status:** `FROZEN_BEFORE_OUTCOMES`

## Research question

Does the sign of aggressive BTCUSDT flow in the first 10 seconds after a quarter-hour boundary
produce positive net expectancy over the replicated 12-hour horizon after Lynxion's conservative
retail execution costs and actual funding?

This is an economic falsification test of the TASK-0386 association. It is not authorization to
create or change a production strategy.

## Unopened chronological boundary

- Discovery/replication period: mechanically sampled dates from `2024-01-01` through `2025-12-01`.
- Holdout period: every complete UTC day from `2026-01-01` through `2026-08-28`, inclusive.
- The 2026 Lead-B flow/return outcomes must not be inspected before this document and the companion
  manifest are committed.
- Existing use of these files by unrelated research does not make this a prospective cohort. This
  is a chronological holdout that was unopened for Lead B; it must never be described as prospective.

## Frozen event and trade construction

- Venue/instrument evidence: retained Binance USD-M `BTCUSDT` aggTrades.
- Evaluate exactly two non-overlapping decision boundaries per day: `00:00:00` and `12:00:00` UTC.
- Observation window: `[boundary, boundary + 10 seconds)`.
- Signed imbalance:
  `(buyer_taker_notional - seller_taker_notional) / total_taker_notional`.
- `LONG` when imbalance is strictly positive; `SHORT` when strictly negative; zero is `NO_TRADE`.
- Entry: first raw trade at or after `boundary + 10 seconds`, with maximum delay 10 seconds.
- Exit: first raw trade at or after `entry target boundary + 12 hours`, with maximum delay 10
  seconds. There is no SL, TP, trailing rule, or intra-trade retuning in this diagnostic.
- The two daily positions cannot overlap. Missing observation, entry, exit, hash, or funding
  integrity makes that event ineligible; no nearest-candle substitution is allowed.
- No leverage is applied to return calculations. Leverage cannot create expectancy.

The fixed `00:00` and `12:00` schedule is a deployment-realistic low-turnover sample, not a claim
that those clock phases are superior. Results must be reported separately for both clock phases;
failure of either phase fails the breadth gate.

## Frozen costs and funding

- Primary round-trip execution friction: `0.30%` of notional.
- Stress round-trip execution friction: `0.50%` of notional.
- These include fee, spread, slippage, and latency allowance; do not replace them with observed
  favorable fills after outcomes.
- Add actual point-in-time Binance BTCUSDT funding settlements strictly after entry and at or before
  exit. Positive funding is paid by LONG and received by SHORT; negative funding is the reverse.
- Report gross directional return, funding return, primary net return, and stress net return.

## Frozen statistics

- Nominal N and eligible UTC-day clusters.
- Primary and stress net expectancy per trade.
- Profit factor, win rate, average win/loss, payoff ratio, and peak-to-trough equity drawdown.
- Day-block bootstrap 95% interval with seed `387` and 5,000 draws.
- Results split by `00:00`/`12:00`, LONG/SHORT, and two chronological folds:
  `2026-01-01..2026-04-30` and `2026-05-01..2026-08-28`.
- A UTC day is the independence cluster; two trades on the same day are not independent samples.

## Frozen integrity gate

- At least 200 eligible UTC days and 400 eligible trades.
- All source ZIP hashes match the retained manifest.
- No entry occurs before the 10-second observation window is complete.
- No exit precedes entry, and no event has more than 10 seconds of entry/exit delay.
- Funding provenance covers every eligible holding interval without silent zero substitution.

Failure of integrity yields `INVALID_DATA`, not KEEP or REJECT.

## Frozen economic verdict

`KEEP_FOR_PROSPECTIVE_CONFIRMATION` requires all of:

1. primary net expectancy strictly positive;
2. day-block bootstrap 95% interval for primary net expectancy strictly above zero;
3. primary profit factor greater than 1.10;
4. primary net expectancy positive in both chronological folds;
5. primary net expectancy positive at both `00:00` and `12:00` phases;
6. neither LONG nor SHORT contributes more than 80% of absolute gross profit;
7. stress-cost expectancy at 0.50% round trip is non-negative;
8. peak-to-trough drawdown is no worse than 20% on an unlevered sequential one-unit return curve.

If integrity passes but any economic gate fails, verdict is `REJECT_ECONOMIC_EDGE`. No threshold,
horizon, phase, side, or cost retuning is allowed on this holdout. A KEEP verdict permits only a new
empty prospective confirmation; it does not permit production promotion.

## Engineering budget

- One disposable evaluator script.
- One focused unit-test file.
- One machine-readable report and one task record.
- No runtime service, broker integration, strategy module, database, or new download.

## خلاصه ساده فارسی

نتیجه مثبت قبلی هنوز سود نیست. حالا قبل از دیدن داده‌های ۲۰۲۶، دقیقاً قفل کردیم که روزی دو بار،
۱۰ ثانیه جریان خریدوفروش را ببینیم، بعد وارد شویم و ۱۲ ساعت نگه داریم. کارمزد، لغزش و funding
همگی از سود کم می‌شوند. اگر نتیجه در دو بازه زمانی، دو ساعت ورود و هزینه سنگین پایدار نباشد، این
سرنخ رد می‌شود و با تغییر threshold نجاتش نمی‌دهیم.
