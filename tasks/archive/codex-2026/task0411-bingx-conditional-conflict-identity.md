# TASK-0411 — BingX conditional-conflict identity

## خلاصه ساده فارسی

هنگام تعارض حدضرر/حدسود، کد قبلاً مقدار خالی `orderId` را به رشته `None` تبدیل و برای لغو ارسال
می‌کرد و پاسخ retry را فقط با قالب قدیمی می‌خواند. اکنون شناسه معتبر exchange یا client انتخاب
می‌شود، مقدار گمشده لغو نمی‌شود و پاسخ retry با قالب فعلی BingX خوانده می‌شود.

## Verified boundary

- Conditional conflict recovery lists stale STOP/TAKE_PROFIT orders before one bounded retry.
- `str(None)` made a missing numeric identity truthy and could issue cancel for literal `None`.
- Both retry-success branches still parsed only legacy nested `data.order.orderId`.

## Minimal correction

- Select `orderID`, `orderId`, then `clientOrderId` from a pending-order record.
- Skip cancellation when all identities are absent.
- Reuse the current/legacy response extractor for both retry-success branches.
- Preserve retry counts, delays, priority admission, protection policy, and conflict codes.

## Validation

- A regression simulates conflict, a stale order with only client identity, and current direct
  `orderID` on retry success.
- Thirty-one focused final-gate, protection, idempotency, retry, and stop-priority tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not edge evidence.

## Next

Inspect conditional request numeric/identity validation before its first authenticated request;
avoid broad refactoring.
