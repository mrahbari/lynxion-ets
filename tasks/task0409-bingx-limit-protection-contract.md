# TASK-0409 — BingX LIMIT attached-protection contract

## خلاصه ساده فارسی

سفارش LIMIT قبلاً حدضرر و حدسود را با کلیدهای غیررسمی `stopLossPrice` و `takeProfitPrice` می‌فرستاد
و ممکن بود سفارش بدون محافظ معتبر ثبت یا رد شود. اکنون این دو محافظ با JSON رسمی `stopLoss` و
`takeProfit`، قیمت عددی و نوع STOP/TAKE_PROFIT_MARKET ارسال می‌شوند.

## Verified boundary

- Market entries already create separate conditional protection orders.
- LIMIT entries used undocumented scalar keys and then assumed protection was attached.
- The current official BingX contract requires JSON-string `stopLoss`/`takeProfit` objects whose
  nested stop prices are JSON numbers, not strings.
- Source: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md

## Minimal correction

- Serialize LIMIT stop loss as `stopLoss={type, stopPrice, workingType}`.
- Serialize LIMIT take profit as `takeProfit={type, stopPrice, workingType}`.
- Keep the already validated/formatted prices numeric inside JSON.
- Preserve MARKET's separate guaranteed-protection path and all strategy/risk settings.

## Validation

- A payload regression rejects the former scalar keys and checks exact nested objects/numeric types.
- Existing market-protection regressions must continue to pass.
- Twenty-seven focused final-gate, protection, idempotency, and retry tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is local request-contract correctness, not proof of live exchange acceptance.

## Next

Review whether a successful LIMIT response proves attached protection visibility or needs a later
broker-visible verification gate; do not infer visibility from request acceptance alone.
