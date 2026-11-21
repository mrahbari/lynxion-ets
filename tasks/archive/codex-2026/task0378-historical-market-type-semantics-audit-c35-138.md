# TASK-0378 — Historical market-type semantics audit and C-35 checkpoint 138

## خلاصه ساده فارسی

یک ریسک داده‌ای مهم تأیید شد: سیستم معاملات perpetual انجام می‌دهد، اما historical provider فقط
نام صرافی را می‌گیرد و مشخص نمی‌کند داده Spot است یا Futures. مسیرهای فعلی Binance و MEXC از
namespace اسپات استفاده می‌کنند و cache هم Spot و perpetual را از هم جدا نمی‌کند. بنابراین حتی
داده کامل می‌تواند متعلق به بازار اشتباه باشد. فعلاً endpoint را کورکورانه عوض نکردیم؛ ابتدا باید
market type در قرارداد صریح و mapping رسمی صرافی‌ها تأیید شود. C-35 سالم به ۱۳۸ تصمیم بدون
سیگنال رسید. collector عمومی C-33 نیز پس از توقف دوباره فعال شد.

## Scope

Audit historical-data market semantics from live strategy buffer through provider, endpoint, and
cache. Do not change endpoints, strategy policy, broker execution, symbols, runtime, or account.

## Evidence and decision

- Default preferred history source is Binance; live strategy fallback includes MEXC/Phemex/BingX.
- Request, registry, cache, and candle contracts contain no Spot/perpetual identity.
- Binance and MEXC paths use Spot `/api/v3/klines` namespaces while reviewed execution is perpetual.
- A complete Spot response may therefore silently satisfy a perpetual strategy buffer.
- Verdict: `BLOCKED — EXPLICIT MARKET-TYPE CONTRACT AND OFFICIAL ENDPOINT MAPPING REQUIRED`.
- C-35 passes integrity with 20,700 candles, 3,312 prospective records, 102 funding records, and 636
  receipts. One no-signal decision advances it to 138; economics remain sealed.
- C-33 stopped with 1,096 eligible buckets and zero active sessions; its already-authorized
  public-only supervisor was resumed without backfill and verification returned one active session.

## Next

Verify current official public candle endpoints for Spot and USDT perpetual markets, then implement
the smallest explicit market-type contract and fail-closed source mapping. This requires no broker
authentication or production policy change.
