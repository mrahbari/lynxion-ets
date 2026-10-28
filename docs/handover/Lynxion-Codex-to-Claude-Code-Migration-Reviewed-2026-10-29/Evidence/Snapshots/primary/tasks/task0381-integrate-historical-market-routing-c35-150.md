# TASK-0381 — Integrate fail-closed historical market routing and C-35 checkpoint 150

## خلاصه ساده فارسی

قرارداد تفکیک Spot و perpetual به مسیر واقعی historical provider وصل شد. درخواست بدون نوع بازار
رد می‌شود، cache کوتاه‌مدت نوع بازار را در کلید دارد و مسیر perpetual فقط به endpoint رسمی
Binance Futures می‌رود. اگر BingX یا fallback دیگری هنوز mapping تأییدشده نداشته باشد، سیستم به
Spot یا فایل محلی ناشناخته سقوط نمی‌کند و بدون داده/سیگنال می‌ماند. این تغییر در کد و تست‌هاست؛
runner یا حساب صرافی دست‌کاری نشد. C-35 سالم به ۱۵۰ تصمیم بدون سیگنال رسید و edge تازه‌ای نداریم.

## Scope

Integrate the TASK-0380 request contract into the configurable and enhanced history paths. Preserve
fail-closed behavior; do not start/reload runtime or change broker/account/strategy/risk policy.

## Evidence and verification

- `ConfigurableHistoricalDataProvider.get_historical_data` now requires explicit `MarketType`.
- Binance perpetual requests route only to `https://fapi.binance.com/fapi/v1/klines`.
- Unverified source/market combinations raise and advance only to another explicit same-market
  source; they cannot default to Binance Spot.
- Enhanced execution history requests perpetual data, isolates its short cache key, and refuses
  legacy Spot/local/download fallback if verified perpetual data is unavailable.
- Focused market contract, routing, and coverage suite: 11 passed.
- C-35 passes integrity with 20,988 candles, 3,600 prospective records, 108 funding records, 654
  receipts, and 150 no-signal decisions; economics remain sealed.
- C-33 remains healthy with one active public session and 1,129 eligible completed buckets.
- C-11 is not due before its eight-hour interval and remains unchanged.

## Next

Run the broader provider/strategy regression surface and resolve any compatibility failures without
weakening the explicit market boundary. Keep unresolved BingX/MEXC/Phemex mappings disabled.
