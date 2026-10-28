# TASK-0399 — BingX final exchange-boundary numeric admission

## خلاصه ساده فارسی

یک لایه ایمنی دیگر بسته شد: بعضی مسیرهای recovery متد پایین‌سطح BingX را مستقیم صدا می‌زنند و
ممکن بود کنترل‌های عددی بالادست را دور بزنند. اکنون درست قبل از هر درخواست صرافی، quantity، price،
stop، SL و TP دوباره بررسی می‌شوند و مقدار صفر، منفی، `NaN` یا بی‌نهایت بدون هیچ POST رد می‌شود.

## Verified boundary

- `_execute_order_after_admission` documents that recovery/service paths may call it directly.
- Its previous final gate checked only symbol blacklist before formatting numeric values.
- Python formatting accepts NaN/Infinity strings, so a direct caller could reach the authenticated
  request boundary without the upstream risk gate.

## Minimal correction

- Require quantity to be present, positive, and finite.
- When present, require price, stop price, stop-loss price, and take-profit price to be positive and
  finite.
- Reject malformed numeric wrappers before symbol formatting, precision lookup, or broker request.
- Preserve leverage, sizing, strategy, thresholds, routing, and protection policy.

## Validation

- Four regressions cover non-finite quantity, price, SL, and TP on the direct low-level path.
- Tests assert that no broker request executes.
- No runtime reload, broker call, order/account mutation, or production-policy change occurred.
- This is correctness evidence, not edge evidence.

## Next

Run the focused BingX protection/admission regressions, then inventory the next independently
verified local fail-open boundary rather than expanding scope.
