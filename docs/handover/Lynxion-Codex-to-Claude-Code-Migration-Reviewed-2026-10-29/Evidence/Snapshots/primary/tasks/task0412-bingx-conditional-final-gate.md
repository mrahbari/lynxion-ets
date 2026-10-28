# TASK-0412 — BingX conditional final gate

## خلاصه ساده فارسی

مسیر حدضرر/حدسود مستقیم می‌توانست مقدارهایی مثل NaN، قیمت نامعتبر، جهت HOLD یا نوع سفارش LIMIT
را تا درخواست احراز هویت‌شده ببرد. اکنون قبل از تماس با صرافی، مقدار و هویت کامل سفارش محافظ
بررسی و در صورت خرابی fail-closed رد می‌شود.

## Verified boundary

- Conditional orders bypass entry admission intentionally because they reduce/protect existing risk.
- That bypass must not permit malformed numeric or identity fields to reach BingX.
- Formatting `NaN`/`Infinity` did not itself provide a fail-closed guarantee.

## Minimal correction

- Require positive finite quantity and stop price.
- Require BUY/SELL, STOP_MARKET/TAKE_PROFIT_MARKET, and LONG/SHORT/BOTH.
- Normalize validated identity fields before serialization.
- Do not apply entry whitelist/blacklist gates to protective exits and do not change stop policy.

## Validation

- Five regressions reject nonfinite quantity/price and invalid side/type/position side without a
  broker request.
- Thirty-six focused final-gate, protection, idempotency, retry, and stop-priority tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not edge evidence.

## Next

Inspect conditional symbol identity without blocking risk-reducing exits for symbols later removed
from the entry allowlist.
