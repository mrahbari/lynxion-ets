# TASK-0414 — BingX VST LIMIT protection verification

## خلاصه ساده فارسی

endpoint آزمایشی BingX یک سفارش DOGEUSDT از نوع LIMIT و PostOnly با ارزش ۱۹٫۹۶۵۰۲ USDT را پذیرفت
و readback همان API هر دو محافظ `STOP_MARKET` و `TAKE_PROFIT_MARKET` را با قیمت دقیق برگرداند.
سفارش سپس لغو شد و audit نهایی صفر سفارش و صفر پوزیشن را گزارش کرد. اپراتور این سفارش را در پنل
VST خود ندید؛ بنابراین تطابق این محیط API با حساب قابل‌مشاهده و مسیر کامل runner هنوز اثبات نشده است.

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

## Evidence correction

The API acceptance/readback evidence is reproducible, but the operator could not find this order in
the visible BingX VST history. The harness also bypassed the platform orchestration and Telegram
notification path. Therefore this task cannot claim UI-account visibility or end-to-end platform
execution. No new order was sent while resolving this discrepancy.

## Verdict

`API_VST_ACCEPTED — UI_ACCOUNT_UNVERIFIED — END_TO_END_PENDING — CLEANUP_PASS`.

This proves only the configured API endpoint's acceptance/readback contract and cleanup for this
controlled case. It does not prove visibility in the operator's VST UI, full-runner execution,
Telegram delivery, profitability, universal symbol compatibility, live-funds readiness, or trailing
behavior.

## Next

When the operator later starts the runner, preserve single-runner admission and verify one platform
event across BingX UI history, execution journal, and Telegram before closing the end-to-end gate.
