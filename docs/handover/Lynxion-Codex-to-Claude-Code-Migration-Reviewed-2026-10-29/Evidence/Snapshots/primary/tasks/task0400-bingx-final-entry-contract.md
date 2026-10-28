# TASK-0400 — BingX final entry-contract admission

## خلاصه ساده فارسی

مسیر پایین‌سطح BingX علاوه بر اعداد، اکنون نوع دستور را هم fail-closed بررسی می‌کند. فقط BUY/SELL
و MARKET/LIMIT برای entry پذیرفته می‌شوند؛ مقدارهایی مثل HOLD یا نوع سفارش ناشناخته قبل از هر
درخواست صرافی رد می‌شوند. این تغییر strategy یا policy نیست، بلکه جلوگیری از ارسال intent خراب است.

## Verified boundary

- Direct recovery/service callers can reach `_execute_order_after_admission` without the normal
  high-level entry path.
- Before this task, arbitrary side strings became `positionSide=BOTH`, and arbitrary order-type
  strings were serialized into the broker request.
- The exchange might reject them, but relying on external rejection is fail-open local admission.

## Minimal correction

- Final entry side must be exactly `BUY` or `SELL` after enum/string normalization.
- Final entry order type must be exactly `MARKET` or `LIMIT`.
- Protective `STOP_MARKET` and `TAKE_PROFIT_MARKET` orders remain on their separate conditional
  order function and are not affected.
- Preserve strategy, position-side, leverage, sizing, SL/TP, and routing policy.

## Validation

- Two new regressions reject unknown side and order type without a broker request.
- Combined final numeric/protection suite: 12 focused tests pass.
- No broker call, runtime reload, order/account mutation, or production-policy change occurred.
- This is correctness evidence, not edge evidence.

## Next

Inspect whether final symbol and position-side identity are already fail-closed before considering
another patch; do not broaden into adapter refactoring.
