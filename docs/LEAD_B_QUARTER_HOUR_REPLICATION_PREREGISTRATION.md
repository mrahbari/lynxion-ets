# Lead B — Quarter-Hour Raw-Flow Replication Preregistration

**Frozen before outcome extraction:** 2026-09-17

## خلاصه ساده فارسی

آزمون Lead B قبل از دیدن بازده‌ها قفل شد. فقط BTCUSDT perpetual در Binance و ۲۴ روز که به‌صورت
مکانیکی انتخاب شده‌اند بررسی می‌شود. فعالیت ۱۰ثانیه اول هر ربع‌ساعت با دو پنجره کنترل همان بلوک
مقایسه می‌شود. تنها اگر اثر فعالیت و رابطه flow با بازده ۴، ۸ و ۱۲ ساعت پایدار باشد، Lead B اجازه
ورود به آزمون اقتصادی مستقل می‌گیرد. این تحلیل strategy یا candidate نیست و production را تغییر
نمی‌دهد.

## Status and scope

`EXPLORATORY REPLICATION ONLY — NOT EDGE EVIDENCE`.

- Venue/contract: Binance USD-M `BTCUSDT` perpetual only.
- Raw source: retained official daily aggTrade ZIP archives.
- Date selection: for each calendar month from 2024-01 through 2025-12, choose the earliest UTC day
  whose normalized integrity record has exactly 96 fifteen-minute rows and whose raw ZIP exists.
  This creates 24 dates without inspecting flow or future returns.
- Chronological folds: 2024-H1, 2024-H2, 2025-H1, 2025-H2.
- Unit of analysis: one quarter-hour boundary event, clustered by UTC day.
- Boundaries: every `HH:00`, `HH:15`, `HH:30`, and `HH:45`.

## Frozen windows and variables

For boundary time `t`:

- Opening window: `[t, t + 10 seconds)`.
- Matched controls in the same quarter-hour block:
  - `[t + 5 minutes, t + 5 minutes + 10 seconds)`;
  - `[t + 10 minutes, t + 10 minutes + 10 seconds)`.
- Raw variables per window:
  - aggTrade count;
  - quote notional `price * quantity`;
  - buyer-initiated quote notional, where `is_buyer_maker == false`;
  - seller-initiated quote notional, where `is_buyer_maker == true`;
  - signed imbalance `(buyer - seller) / (buyer + seller)`;
  - first-to-last log price change;
  - realized absolute log-return path within the window.

Future return horizons are fixed at 4h, 8h, and 12h from the boundary using the already-normalized
15-minute price panel. No alternative horizon may be added after seeing results.

## Integrity gates before outcomes

- Every selected ZIP hash must match its recorded checksum/manifest hash.
- Raw schema, timestamps, IDs, numeric fields, and aggressor-side values must pass the existing
  manifest checks.
- Each selected day must have exactly 96 normalized 15-minute rows.
- No boundary event may use an incomplete opening/control window silently; missing events are
  reported and excluded before outcome join.
- Coverage is reported by fold and UTC hour.
- If fewer than 20 of 24 selected days pass integrity, verdict is
  `INSUFFICIENT_DATA — REJECT THIS MINIMAL REPLICATION`.

## Frozen replication questions

1. Are opening-window trade count, quote volume, and absolute price movement larger than the mean of
   their two matched controls?
2. Does signed opening imbalance have incremental association with 4h/8h/12h returns after
   controlling for the contemporaneous 15-minute return and log volume?
3. Is the sign of the relationship stable across at least three of four chronological folds?

Use paired event differences, UTC-day clustered uncertainty, and a day-block bootstrap. Report
nominal events and 24 day clusters; never call quarter-hour observations independent samples.

## Frozen decisions

`REJECT TRANSFERABILITY` if any of the following holds:

- integrity gate fails;
- boundary activity is not greater than matched controls in aggregate or has opposite/unstable fold
  behavior;
- imbalance/return association has inconsistent signs in more than one chronological fold;
- day-block bootstrap intervals include economically negligible zero-like effects at all three
  horizons;
- apparent evidence is dominated by one fold or a small number of days.

`PREREGISTER ECONOMIC TEST NEXT` only if:

- integrity passes;
- the boundary-activity effect replicates;
- at least one predeclared 4h/8h/12h relationship is sign-stable in at least three folds and its
  day-block interval excludes zero;
- the effect is not concentrated in one fold or fewer than six UTC days.

Survival does not prove edge. It only permits a new unopened economic test with fees, spread,
slippage, latency, turnover, stress costs, and `NO_TRADE_DEFAULT`.

## Engineering budget

- Maximum new implementation for replication: one disposable analysis script, one focused test,
  one JSON report.
- No service, collector, database, production strategy, ML model, or new download.
- Expected execution time: hours, bounded by reading 24 existing ZIP archives.
