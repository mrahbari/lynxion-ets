# TASK-0407 — BingX adapter retry idempotency

## خلاصه ساده فارسی

شناسه ضدتکرار قبلاً روی کپی موقت سفارش ساخته می‌شد، نه روی سفارش اصلی. اگر همان سفارش از سطح
adapter دوباره تلاش می‌شد، کپی جدید می‌توانست شناسه تازه بگیرد و خطر ثبت سفارش تکراری ایجاد کند.
اکنون شناسه قبل از ساخت کپی روی سفارش اصلی تثبیت و در همه retryها دوباره استفاده می‌شود.

## Verified boundary

- `BingXBrokerAdapter.place_order` creates a formatted temporary `Order` for each call.
- When the original had no client ID, the low-level broker generated one only on that temporary copy.
- Retrying the same original logical order could therefore create a new exchange idempotency key.

## Minimal correction

- Generate or preserve the client order ID on the original order before copying it.
- Pass that exact ID to every formatted temporary order.
- Preserve request shape, strategy, risk, sizing, symbol policy, and routing.

## Validation

- A regression calls adapter `place_order` twice with the same object and requires one stable ID.
- Twenty-four focused final-gate, protection, idempotency, and retry tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not edge evidence.

## Next

Define safe reconciliation for a nominal BingX success response that omits order identity, using the
now-stable original client order ID and without automatic blind retry.
