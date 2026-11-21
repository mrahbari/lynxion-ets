# TASK-0398 — Non-finite SL/TP sanitization

## خلاصه ساده فارسی

یک حفره واقعی پیدا و بسته شد: اگر stop-loss یا take-profit به شکل `NaN` یا بی‌نهایت وارد مسیر
ساخت سفارش می‌شد، مقایسه‌های معمول پایتون آن را نامعتبر تشخیص نمی‌دادند و مقدار خراب می‌توانست تا
درخواست broker باقی بماند. اکنون این مقادیر به SL/TP پیش‌فرض و محدود تبدیل می‌شوند و entry نامتناهی
کاملاً fail-closed می‌شود. threshold یا استراتژی تغییر نکرده است.

## Verified defect

- `sanitize_sltp_levels` checked only `<=`, `>=`, and positivity.
- Python comparisons against `NaN` are false, allowing non-finite SL/TP to bypass all repair branches.
- `MultiBrokerExecutionService._enhance_order_with_risk_parameters` calls this utility on the
  production order-enhancement path and then constructs `Money` values from its output.

## Minimal correction

- Reject non-finite entry price by returning the existing fail-closed `(0.0, 0.0)` sentinel.
- Treat non-finite requested SL/TP as absent, invoking the existing side-aware defaults and caps.
- Preserve all configured percentages, thresholds, side semantics, and broker routing.

## Validation

- Regressions cover NaN/infinite entry, NaN/infinite LONG protection, and the integrated
  multi-broker enhancement path.
- No broker call, runtime reload, account/order mutation, or strategy/risk-policy change.
- This is correctness evidence, not edge evidence.

## Next

Run the focused risk/order suite and continue inspecting final exchange-boundary numeric admission
without broad refactoring.
