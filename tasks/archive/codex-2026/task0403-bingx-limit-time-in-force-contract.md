# TASK-0403 — BingX limit-order time-in-force contract

## خلاصه ساده فارسی

سفارش LIMIT در مسیر BingX قبلاً قیمت و شیوه ماندگاری سفارش را به‌طور کامل تضمین نمی‌کرد.
اکنون LIMIT بدون قیمت یا با time-in-force ناشناخته قبل از تماس با صرافی رد می‌شود و مقدار معتبر
`POST_ONLY` با قالب رسمی `PostOnly` ارسال می‌شود.

## Verified boundary

- The domain carries `time_in_force`, but the BingX request omitted it.
- A LIMIT order could reach request construction without a price.
- The official BingX swap reference requires price/time-in-force for LIMIT and documents
  `GTC`, `IOC`, `FOK`, and `PostOnly`.
- Source: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md

## Minimal correction

- Require a price for LIMIT orders.
- Accept only the documented LIMIT time-in-force values.
- Map Lynxion's existing `POST_ONLY` spelling to BingX `PostOnly` and include `timeInForce`.
- Leave MARKET requests and all strategy/risk settings unchanged.

## Validation

- Regressions reject missing LIMIT price and unknown time-in-force before a broker request.
- A payload regression proves `POST_ONLY` becomes `timeInForce=PostOnly`.
- Twenty-two focused final-gate, protection, and idempotency tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not edge evidence.

## Next

Inspect the BingX request field name used for the client order ID against the current official
contract before considering another bounded correction; do not infer exchange acceptance locally.
