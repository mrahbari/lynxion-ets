# TASK-0401 — BingX final symbol and position identity contract

## خلاصه ساده فارسی

آخرین مرز ارسال سفارش BingX اکنون فقط نمادهای فهرست مجاز و position side معتبر را قبول می‌کند.
نماد ناشناخته یا مقدارهایی مثل `UP` قبل از هر تماس با صرافی رد می‌شوند. این اصلاح، استراتژی یا
سیاست نمادها را تغییر نمی‌دهد؛ همان سیاست موجود را برای مسیرهای پایین‌سطح نیز اجباری می‌کند.

## Verified boundary

- Normal entry admission already uses the configured symbol policy, but a direct low-level caller
  could previously serialize an unknown, non-blacklisted symbol.
- An explicit arbitrary `position_side` string could also reach the authenticated request.
- Exchange-side rejection is not a substitute for local fail-closed identity validation.

## Minimal correction

- Normalize the requested symbol and require membership in the existing approved-symbol set.
- Preserve the existing dynamic blacklist as an additional final gate.
- When `position_side` is explicit, require `LONG`, `SHORT`, or `BOTH`; preserve the existing
  side-based inference when it is absent.
- Do not change symbol admission policy, strategy, leverage, sizing, SL/TP, or routing.

## Validation

- Regressions reject an unknown symbol and malformed position side without a broker request.
- Fourteen focused final-gate/protection tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change is allowed.
- This is correctness evidence, not edge evidence.

## Next

Inspect remaining final request metadata such as time-in-force/client identity before considering
another bounded patch; do not broaden into adapter refactoring.
