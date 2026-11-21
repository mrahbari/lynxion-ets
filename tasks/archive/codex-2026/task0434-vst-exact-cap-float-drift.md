# TASK-0434 — VST exact-cap float-drift correction

## خلاصه ساده فارسی

یک سفارش که دقیقاً ۲۱ دلار بود می‌توانست در محاسبه‌ی float مقدار
`21.000000000000004` شود و اشتباهاً به‌عنوان عبور از سقف ۲۱ دلار رد شود. اکنون فقط وقتی محاسبه
دقیق Decimal ثابت کند سفارش داخل سقف است، quantity به‌اندازه یک گام بسیار کوچک پایین آورده می‌شود
تا بررسی float هم از سقف عبور نکند. سقف ریسک افزایش پیدا نکرده است.

## Scope

- Handle only exact-cap Decimal orders that drift above the cap after float conversion.
- Reduce executable quantity by one float step; never relax the configured limit.
- Add a regression for the reproducible `300 × 0.07` boundary case.

## Verification

`pytest -q tests/unit/test_risk_enforcement.py -q`

Result: 30 passed.

## Verdict

`KEEP — VERIFIED NUMERIC CORRECTNESS FIX; VST CAP UNCHANGED`.

No strategy, trailing, leverage, symbol admission, broker/account state, or frozen research protocol
was changed. This is not edge evidence.
