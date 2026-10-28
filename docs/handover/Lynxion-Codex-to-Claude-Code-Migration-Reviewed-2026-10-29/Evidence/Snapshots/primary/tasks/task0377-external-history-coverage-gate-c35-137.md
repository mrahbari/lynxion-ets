# TASK-0377 — External historical-data coverage gate and C-35 checkpoint 137

## خلاصه ساده فارسی

یک حفره واقعی در data provider پیدا و بسته شد: پاسخ API با سقف ۵۰۰ یا ۱۰۰۰ کندل می‌توانست برای
درخواست بزرگی مثل ۳۰ روز، «موفق» تلقی و cache شود؛ حتی اگر بیشتر بازه وجود نداشت. اکنون هر پاسخ
external و cache باید حداقل ۹۵٪ تعداد کندل موردانتظار را داشته باشد، timestampهای تکراری کمکی
نمی‌کنند و آخرین کندل نیز باید تازه باشد. داده ناقص fail-closed رد می‌شود و provider سراغ منبع
بعدی می‌رود. این اصلاح کیفیت ورود داده است و ادعای edge ندارد. C-35 سالم به ۱۳۷ تصمیم بدون
سیگنال رسید.

## Scope

Close the verified external-history coverage bypass in `ConfigurableHistoricalDataProvider` with a
minimal fail-closed gate and focused tests. Do not alter symbol admission, strategy logic, broker
execution, production runtime, or the frozen 5% missing-data threshold.

## Evidence and fix

- Direct exchange methods request only one API page (500/1,000 candles) and previously accepted any
  non-empty response for periods such as 30 days.
- The provider now derives expected count from period/timeframe, counts unique in-window timestamps,
  requires missing ratio <=5%, and requires a fresh latest candle.
- Millisecond timestamps are normalized for validation. Invalid period/timeframe/timestamps,
  duplicate-inflated data, stale data, and short pages fail closed.
- An incomplete preferred source is neither cached nor returned; the provider may use a complete
  fallback. Incomplete cached fallback is also rejected.
- Focused data-integrity/coverage suite: `16 passed`.
- C-35 passes integrity with 20,676 candles, 3,288 prospective records, 102 funding records, and 630
  receipts. Two no-signal decisions advance it from 135 to 137; economics remain sealed.
- C-33 remains healthy with one active session and 1,094 eligible buckets.

## Decision

`KEEP — EXTERNAL/CACHED HISTORY NOW FAILS CLOSED ON INCOMPLETE OR STALE COVERAGE`.

No runtime was reloaded and no broker/account/order state changed. Deployment verification remains
separate from repository correctness.
