# TASK-0410 — BingX LIMIT protection verification gate

## خلاصه ساده فارسی

قالب محلی حدضرر و حدسود LIMIT اکنون با مستند رسمی هماهنگ و با تست ثابت شده است، اما تست محلی
نمی‌تواند ثابت کند BingX واقعاً محافظ‌ها را پذیرفته و نمایش داده است. برای اثبات نهایی باید در حساب
VST یک سفارش کنترل‌شده ثبت و سپس با query فقط‌خواندنی، محافظ‌ها مشاهده شوند؛ این مرحله بدون مجوز
اجرای صرافی انجام نشد.

## Local evidence

- TASK-0409 serializes exact official `stopLoss`/`takeProfit` JSON-string fields.
- Nested `stopPrice` values are numeric and validated positive/finite before request construction.
- Existing MARKET protection remains a separate conditional-order path with unwind-on-failure.
- Twenty-seven focused request/protection/idempotency tests passed at TASK-0409.

## What local evidence cannot prove

- That the VST endpoint accepts both nested objects for the account's current mode.
- That accepted LIMIT protection is visible before fill and remains attached after fill.
- That the returned/open-order representation preserves both trigger prices and types.
- That a rejected nested protection cannot coexist with an accepted unprotected LIMIT entry.

## Frozen external verification gate

Only after explicit execution approval:

1. Use VST/testnet only and one approved, liquid symbol with minimum safe notional.
2. Place one non-marketable LIMIT with deterministic `clientOrderId`, SL, and TP.
3. Read back the parent order and attached protection by client ID.
4. Require exact symbol, side, position side, quantity, SL/TP types, and trigger prices.
5. Cancel the still-unfilled parent and verify no residual conditional orders or position.
6. Record all broker responses with secrets removed.

Any missing/ambiguous protection is `FAIL_CLOSED`; do not promote local readiness from request tests.

## Decision

`LOCAL_CONTRACT_READY — BROKER_VISIBILITY_APPROVAL_GATED`.

No authenticated query, order placement, cancellation, runtime reload, account mutation, or policy
change occurred in this task. Continue independent local correctness work and frozen edge collection.

## Next

Inspect the next bounded BingX contract locally. Keep this gate parked until explicit permission for
the controlled VST order plus cleanup is given.
