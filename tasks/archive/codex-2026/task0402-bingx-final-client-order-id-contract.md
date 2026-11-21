# TASK-0402 — BingX final client-order-id contract

## خلاصه ساده فارسی

شناسه‌ای که برای جلوگیری از ثبت تکراری سفارش به BingX فرستاده می‌شود اکنون در آخرین مرز ارسال
بررسی می‌شود. شناسه دارای علامت نامعتبر یا طول بیشتر از ۴۰ کاراکتر قبل از تماس با صرافی رد می‌شود؛
شناسه خودکار فعلی بدون تغییر باقی مانده است.

## Verified boundary

- Lynxion already generates a stable alphanumeric client order ID for an order without one.
- A caller-supplied ID was preserved without validating the adapter's documented BingX contract.
- An exchange rejection could therefore defeat the intended idempotency protection.

## Minimal correction

- Require the final client order ID to be a string, alphanumeric, and at most 40 characters.
- Preserve existing valid caller IDs and existing generated-ID/retry behavior.
- Do not alter entry, strategy, risk, leverage, symbol, sizing, or exit policy.

## Validation

- Regressions reject a punctuation-bearing ID and a 41-character ID before any broker request.
- Nineteen focused final-gate, protection, and idempotency tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not edge evidence.

## Next

Inspect limit-order time-in-force handling against the adapter's existing contract before considering
another bounded correction; do not broaden into adapter refactoring.
