# TASK-0379 — Official historical market-type mapping and frozen cohort refresh

## خلاصه ساده فارسی

مسیر رسمی کندل‌های Spot و perpetual بررسی شد. برای Binance، MEXC و Phemex تفاوت بازار و مسیر
رسمی روشن است، اما مسیر قدیمی BingX در کد فعلی هنوز ثابت نمی‌کند داده دقیقاً مربوط به perpetual
باشد. بنابراین endpoint را حدس نزدیم و تغییر ندادیم. مرز اصلاح بعدی فریز شد: نوع بازار باید در
درخواست و cache اجباری باشد و fallback هرگز حق ندارد از perpetual به Spot برود. C-11 بدون نتیجه
جدید همان چهار خروجی کامل و یک مورد pending را دارد. C-35 سالم به ۱۴۸ تصمیم بدون سیگنال رسید و
C-33 با یک session فعال به ۱۱۰۵ باکت رسید. هنوز edge اثبات نشده است.

## Scope

Verify official public Spot/perpetual candle contracts, freeze the smallest fail-closed correction
boundary, and advance the three existing background cohorts. Do not change an endpoint, production
policy, runtime, broker/account state, or sealed candidate economics.

## Evidence and decision

- Binance Spot and USD-M futures use distinct official `/api/v3/klines` and `/fapi/v1/klines`
  contracts.
- MEXC Spot and contract markets use distinct hosts, namespaces, symbol formats, and response
  schemas; contract last-price versus fair-price must be an explicit choice.
- Phemex documents separate USD-M perpetual kline list/last contracts; the repository uses a legacy
  path and mismatched parser contract.
- The current BingX path does not prove its market/price-series identity from the reviewed official
  static evidence, so it remains unsupported rather than guessed.
- Verdict: `PARTIAL KEEP — IMPLEMENT EXPLICIT FAIL-CLOSED MARKET TYPE; VERIFY BINGX BEFORE USE`.
- C-11 refresh retained N=4 complete plus one pending record, all settlement timestamps strictly
  after epoch `1788082349`; expectancy remains +0.2524% and PF 1.2693, verdict `COLLECTING`.
- C-35 passes integrity with 20,940 candles, 3,552 prospective records, 108 funding records, 642
  receipts, and 148 no-signal decisions; economics remain sealed.
- C-33 is healthy with one active public session and 1,105 eligible completed buckets.

## Next

Implement the minimum explicit `market_type` request/cache contract and focused Binance USD-M
mapping tests. Unsupported sources must fail closed without crossing market type. Keep BingX
perpetual disabled in this historical-data boundary until its exact official contract is verified.
