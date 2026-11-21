# TASK-0375 — Leverage correctness-state reconciliation and C-35 checkpoint 135

## خلاصه ساده فارسی

یک گزارش قدیمی هنوز طوری نوشته شده بود که انگار حفره fail-open اهرم در کد فعلی باز است. این
حفره در TASK-0135 داخل repository بسته شده و ۴۶ تست فعلی دوباره آن را تأیید کردند. فقط اثبات
deployment و وضعیت واقعی exchange باقی مانده که بدون مجوز نباید انجام شود. مستندات اصلاح شدند تا
تیم فنی defect بسته‌شده را با ریسک deployment اشتباه نگیرد. C-35 نیز سالم به ۱۳۵ تصمیم بدون
سیگنال رسید.

## Scope

Reconcile the stale leverage-risk wording against current source and focused regression evidence.
Do not change leverage, configuration, broker state, runtime, production policy, or order handling.

## Evidence and decision

- TASK-0132 accurately recorded the historical fail-open defect at its audit boundary.
- TASK-0135 subsequently carried requested leverage through the execution contract, added BingX
  set/readback/admission checks, preserved authoritative hydration, and removed the production
  ActivePositionManager fallback.
- Current focused leverage/admission/risk suite: `46 passed`.
- Repository verdict: `KEEP — LOCAL FAIL-CLOSED LEVERAGE CONTRACT VERIFIED`.
- Remaining uncertainty is deployment/account evidence only; no authenticated call or runtime
  reload was performed.
- C-35 passes integrity with 20,628 candles, 3,240 prospective records, 96 funding records, and 624
  receipts. One no-signal decision advances it to 135; economics remain sealed.
- C-33 remains healthy with one active session and 1,069 eligible buckets.

## Next

Inventory the next highest-priority stale/open correctness claim that can be resolved entirely from
current source and local tests. Keep TASK-0359 broker/runtime activation blocked.
