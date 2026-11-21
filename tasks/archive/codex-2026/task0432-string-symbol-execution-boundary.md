# TASK-0432 — Raw string symbol execution-boundary robustness

## خلاصه ساده فارسی

اگر استعلام موقعیت broker خطا می‌داد و نماد سفارش به‌صورت متن ساده بود، خود پیام هشدار با فرض
وجود `.value` خطای دوم می‌ساخت و سفارش قبل از رسیدن به مسیر broker رد می‌شد. اکنون نام نماد یک‌بار
در ابتدای مسیر به شکل امن نرمال می‌شود و همه پیام‌های همان مسیر از مقدار امن استفاده می‌کنند.

## Scope

- Normalize the order symbol display value once at the `BrokerExecutionService.execute_order`
  boundary.
- Remove direct `.value` assumptions from execution-path diagnostics and rejection messages.
- Add a regression reproducing a raw string symbol plus failed position lookup.

## Verification

`pytest -q tests/unit/test_order_side_string_robustness.py -q`

Result: 8 passed.

## Verdict

`KEEP — VERIFIED EXECUTION-CORRECTNESS FIX`.

This change does not alter strategy, risk, sizing, trailing, symbol admission, broker/account state,
or any frozen edge protocol. It is not evidence of profitability or edge.
