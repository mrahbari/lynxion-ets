# TASK-0408 — BingX missing-order-id reconciliation

## خلاصه ساده فارسی

اگر BingX پاسخ موفق بدهد ولی شناسه عددی سفارش را برنگرداند، تکرار کورکورانه خطر ثبت سفارش دوم
دارد. اکنون adapter همان شناسه پایدار `clientOrderId` را برمی‌گرداند و مسیرهای وضعیت، fill و لغو
می‌توانند با آن سفارش را پیدا کنند. بنابراین پاسخ مبهم باعث ساخت شناسه تازه یا retry کور نمی‌شود.

## Verified boundary

- A code-zero response could carry no readable exchange order ID.
- The adapter then returned `None`, even though the exchange may already have accepted the order.
- TASK-0407 makes the original client ID stable, and BingX officially supports query/cancel by it.

## Minimal correction

- On nominal success without exchange identity, return the stable client order ID and log warning.
- Match order status/fill against either `orderId` or `clientOrderId`.
- Cancel numeric identities via `orderId` and nonnumeric client identities via `clientOrderId`.
- Do not automatically resend, query the broker during placement, or change trading policy.

## Validation

- Regressions cover missing exchange identity, client-ID status/fill reconciliation, and cancel key.
- Twenty-six focused final-gate, protection, idempotency, and retry tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not edge evidence.

## Next

Inspect attached LIMIT protection serialization against the official nested `stopLoss`/`takeProfit`
contract without weakening guaranteed-protection behavior.
