# TASK-0380 — Fail-closed historical market contract and C-35 checkpoint 149

## خلاصه ساده فارسی

اولین بخش اصلاح mismatch بازار پیاده شد: هر درخواست تاریخچه باید نوع بازار Spot یا perpetual را
صریح حمل کند و کلید cache این دو را جدا نگه می‌دارد. فعلاً فقط دو مسیر رسمی Binance در mapping
پذیرفته می‌شوند؛ BingX و مسیرهای تأییدنشده به‌جای افتادن روی Spot خطا می‌دهند. این قرارداد هنوز
به runtime وصل نشده، پس رفتار production تغییر نکرده است. C-35 نیز سالم به ۱۴۹ تصمیم بدون سیگنال
رسید؛ edge جدیدی مشاهده نشد.

## Scope

Add the smallest isolated request/cache identity contract and verified Binance endpoint mapping.
Do not connect it to runtime, switch a live endpoint, or change broker, strategy, risk, or symbols.

## Evidence and verification

- `HistoricalMarketRequest` requires an enum-valued explicit market type.
- Cache identity includes source, market type, normalized symbol, and timeframe.
- Binance Spot maps only to `/api/v3/klines`; Binance perpetual maps only to
  `/fapi/v1/klines`.
- BingX perpetual and every other unverified combination fail closed.
- Focused regression: 3 passed.
- C-35 passes integrity with 20,964 candles, 3,576 prospective records, 108 funding records, 648
  receipts, and 149 no-signal decisions; economics remain sealed.
- C-33 is healthy with one active public session and 1,117 eligible completed buckets.
- C-11 was not refreshed before its eight-hour interval; it remains N=4 complete plus one pending.

## Next

Integrate this contract into `ConfigurableHistoricalDataProvider` without permitting cross-market
fallback. Add focused request-routing tests before the live strategy explicitly requests
`PERPETUAL`; do not enable unresolved BingX mapping.
