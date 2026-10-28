# TASK-0404 — BingX client-order-id request field

## خلاصه ساده فارسی

کلید شناسه ضدتکرار سفارش با حروف اشتباه `clientOrderID` ارسال می‌شد، در حالی که قرارداد رسمی
BingX نام دقیق `clientOrderId` را تعریف می‌کند. هر دو مسیر ارسال اصلی اصلاح شدند تا صرافی بتواند
شناسه را بشناسد و retry یک سفارش را تکراری تشخیص دهد.

## Verified boundary

- Lynxion generated and reused a stable client order ID, but serialized it under `clientOrderID`.
- The current official BingX swap contract specifies the case-sensitive field `clientOrderId`.
- Both the ordinary request and the market-plus-protection main request used the wrong spelling.
- Source: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md

## Minimal correction

- Rename only the two outbound payload keys to `clientOrderId`.
- Update the idempotency regressions to assert the official field.
- Preserve identifier generation, reuse, validation, strategy, risk, sizing, and routing.

## Validation

- Twenty-two focused final-gate, protection, idempotency, and retry tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not proof that an exchange accepted a live request.

## Next

Inspect other BingX request fields against the current official contract, one bounded path at a
time; do not perform broad adapter refactoring.
