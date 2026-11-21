# TASK-0406 — BingX precision-safe order identity

## خلاصه ساده فارسی

BingX علاوه بر `orderId` عددی، شناسه `orderID` رشته‌ای ارائه می‌کند چون مقدار عددی ممکن است در
بعضی زبان‌ها دقتش را از دست بدهد. اکنون Lynxion ابتدا نسخه رشته‌ای امن را می‌خواند و فقط در نبود
آن به نسخه عددی یا قالب قدیمی برمی‌گردد.

## Verified boundary

- TASK-0405 restored the current direct response shape but read only numeric `orderId`.
- The current official BingX reference explicitly recommends string `orderID` for precision safety.
- Source: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md

## Minimal correction

- Prefer direct `data.orderID`, then direct `data.orderId`.
- Preserve both legacy nested variants as fallbacks.
- Do not change request construction, strategy, risk, sizing, or routing.

## Validation

- A regression supplies both forms and requires the precision-safe string value.
- Twenty-three focused final-gate, protection, idempotency, and retry tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is local response-contract correctness, not edge evidence.

## Next

Define safe handling for a nominal success response that contains neither identity field, without
creating automatic duplicate-order risk.
