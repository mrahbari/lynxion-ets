# TASK-0405 — BingX order-response identity

## خلاصه ساده فارسی

قرارداد فعلی BingX شناسه سفارش موفق را مستقیماً در `data.orderId` برمی‌گرداند، اما کد فقط قالب
قدیمی `data.order.orderId` را می‌خواند. اکنون هر دو قالب پشتیبانی می‌شوند تا سفارش پذیرفته‌شده با
شناسه خالی ثبت نشود.

## Verified boundary

- All three BingX order-success paths read only the legacy nested response shape.
- The current official swap reference documents `orderId` directly under response `data`.
- A successful current-shape response therefore produced `success=True` with `order_id=None`.
- Source: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md

## Minimal correction

- Add one side-effect-free response extractor preferring `data.orderId`.
- Retain fallback support for legacy `data.order.orderId` responses.
- Use it for ordinary, protected-main, and conditional-order success paths.
- Do not change request construction, strategy, risk, sizing, or routing.

## Validation

- The LIMIT payload regression now uses the current direct response shape and requires `LIMIT1`.
- Twenty-two focused final-gate, protection, idempotency, and retry tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is local response-contract correctness, not proof of live exchange acceptance.

## Next

Inspect success responses that omit order identity and define a fail-closed/reconciliation behavior
without introducing duplicate-order risk.
