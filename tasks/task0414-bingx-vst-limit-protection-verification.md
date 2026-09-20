# TASK-0414 — BingX VST LIMIT protection verification

## خلاصه ساده فارسی

آزمایش کنترل‌شده روی حساب واقعی VST موفق شد. یک سفارش DOGEUSDT از نوع LIMIT و PostOnly با ارزش
۱۹٫۹۶۵۰۲ USDT ثبت شد. BingX در readback هر دو محافظ `STOP_MARKET` و `TAKE_PROFIT_MARKET` را با
قیمت دقیق مورد انتظار نشان داد. سفارش سپس لغو شد و audit نهایی صفر سفارش و صفر پوزیشن را تأیید کرد.

## Controlled scope

- Venue: BingX VST/testnet only.
- No production runner was active before or after the test.
- Symbol: DOGEUSDT; side/position side: BUY/LONG.
- Non-marketable LIMIT at 0.06814 versus reference price 0.08518.
- Quantity: 293; notional: 19.96502 USDT; time-in-force: PostOnly.
- Stop loss: 0.05962; take profit: 0.10221.
- Client identity: `VSTLIMIT20260920120441`.

## Broker evidence

- Accepted exchange order ID: `2101644004010496000`.
- Readback status: `PENDING`, exact symbol/side/position/type/client identity matched.
- Attached stop loss: `STOP_MARKET`, `MARK_PRICE`, trigger 0.05962.
- Attached take profit: `TAKE_PROFIT_MARKET`, `MARK_PRICE`, trigger 0.10221.
- Parent cancellation returned success.
- Final independent audit: zero open positions and zero pending orders.
- Redacted evidence: `data/observability/vst_limit_protection_verification.json`.

## Initial safe rejection

The first BTCUSDT attempt never reached BingX because the local 60-minute cooldown gate rejected it.
No cooldown was bypassed or edited. The harness then used approved DOGEUSDT, which had no cooldown.

## Verdict

`VST_BROKER_VERIFIED — LIMIT_ATTACHED_PROTECTION_VISIBLE — CLEANUP_PASS`.

This proves the corrected LIMIT request path against BingX VST for this controlled case. It does not
prove profitability, universal symbol compatibility, live-funds readiness, or trailing behavior.

## Next

The current source is suitable for a controlled VST platform restart from this checkout. Preserve
single-runner admission and run post-start read-only order/position/protection surveillance.
