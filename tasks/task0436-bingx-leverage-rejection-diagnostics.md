# TASK-0436 — BingX margin/leverage rejection diagnostics

## خلاصه ساده فارسی

لاگ‌ها ۲۹ بار شکست تنظیم isolated margin یا leverage را نشان می‌دادند، اما کد پاسخ واقعی BingX را
حذف و فقط یک پیام عمومی ثبت می‌کرد. اکنون بدون ثبت payload یا اطلاعات حساس، نام مرحله، کد خطا و
پیام امن broker نگه داشته می‌شود تا در اجرای بعدی علت دقیق مشخص شود.

## Scope

- Preserve the rejected operation name (`marginType` or `leverage`).
- Preserve only broker response `code` and `msg`/`message` in the fail-closed reason.
- Do not accept any additional response code or weaken authoritative readback.

## Verification

`pytest -q tests/unit/test_task0135_leverage_contract.py -q`

Result: 14 passed.

## Verdict

`KEEP — VERIFIED EXECUTION DIAGNOSTIC FIX; ADMISSION REMAINS FAIL-CLOSED`.

This does not yet fix the exchange rejection itself; it makes the next controlled VST observation
actionable. No broker call, account mutation, leverage change, or runtime restart occurred.
