# TASK-0386 — Lead-B quarter-hour flow replication

## خلاصه ساده فارسی

اثر فعالیت بازار در ۱۰ ثانیه اول هر ربع‌ساعت روی ۲۴ روز مستقل بررسی شد. تعداد معامله و حجم
در هر چهار بازه زمانی بیشتر بود. عدم‌تعادل خریدوفروش فقط در افق ۱۲ساعته نتیجه‌ای پایدار با بازه
اطمینان خارج از صفر داشت. این نتیجه امیدوارکننده است، اما هنوز سودآوری نیست؛ قدم بعد باید یک
آزمون اقتصادی از پیش قفل‌شده روی داده بازنشده و با همه هزینه‌ها باشد.

## Scope

- Execute only the frozen protocol in
  `docs/LEAD_B_QUARTER_HOUR_REPLICATION_PREREGISTRATION.md`.
- Use the retained raw Binance USD-M BTCUSDT aggTrade archives; do not download new data.
- Preserve C-11, C-33, and C-35 unchanged.
- Do not create or alter a production strategy.

## Evidence

- Integrity passed on all 24 required UTC days.
- Nominal quarter-hour observations: 2,304.
- Effective independent clusters: 24 UTC days.
- Opening-window trade-count excess: `+35.6168`, day-block 95% interval
  `[+21.9261, +47.0878]`, positive in 4/4 chronological folds.
- Opening-window quote-volume excess: `+$579,556`, day-block 95% interval
  `[+$367,104, +$772,981]`, positive in 4/4 chronological folds.
- The 4h and 8h imbalance coefficients were positive but their uncertainty intervals crossed zero.
- The 12h imbalance coefficient was `+0.0017323`, with day-block 95% interval
  `[+0.0003245, +0.0032095]` and the same positive sign in 4/4 folds.
- Focused helper test: 1 passed.
- No fee, spread, slippage, latency, turnover, drawdown, or executable fill model was evaluated.
- Verdict: `PREREGISTER_ECONOMIC_TEST_NEXT`.

## Validation correction

The first implementation used the full current 15-minute candle return as a control even though
that candle closes after the 10-second observation window. That output is invalid and retained only
as `docs/reports/lead_b_clock_replication_invalid_lookahead.json`. The accepted run uses the strictly
completed `[t-15m, t)` return. Dates, windows, horizons, and gates were not retuned after outcomes.

## Monitoring state

- C-11: 5 completed outcomes, descriptive expectancy `+0.5722%`, PF `1.7631`; still
  `COLLECTING`, too small and ETH-concentrated for an edge claim.
- C-35: integrity passes at 22,182 candles, 4,794 prospective records, 150 funding records, 684
  coverage receipts, and 200 `NO_SIGNAL` decisions.
- C-33: 1,167 eligible completed buckets, but its latest public record is dated
  `2026-09-17T17:06:36Z`; freshness requires separate operational attention.

## Next

Freeze one chronological, unopened economic holdout before inspecting its outcomes. Entry must be
after the first 10 seconds, the 12h horizon is primary, and realistic fee, spread, slippage, latency,
turnover, drawdown, clustering, and stress-cost gates must be explicit. A negative net result
rejects the economic lead even if the statistical association remains positive.
