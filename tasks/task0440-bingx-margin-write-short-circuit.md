# TASK-0440 — BingX margin-write short circuit

## خلاصه ساده فارسی

اگر درخواست تنظیم isolated margin رد می‌شد، کد با وجود شکست مرحله اول باز هم درخواست تغییر leverage
را به صرافی می‌فرستاد و سپس کل سفارش را رد می‌کرد. اکنون مراحل به‌ترتیب اجرا می‌شوند و اولین شکست،
ادامه‌ی mutation را متوقف می‌کند.

## Scope

- Execute margin and leverage writes sequentially.
- Stop before leverage mutation when margin establishment fails.
- Preserve fail-closed admission, safe diagnostics, and authoritative readback unchanged.

## Verification

`pytest -q tests/unit/test_task0135_leverage_contract.py -q`

Result: 15 passed.

## Verdict

`KEEP — VERIFIED BROKER-MUTATION CORRECTNESS FIX`.

No broker call was made during this task and no leverage, margin, strategy, risk threshold, or account
state was changed.
