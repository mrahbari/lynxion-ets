# TASK-0438 — Independent unknown-exit reconciliation identity

## خلاصه ساده فارسی

وقتی broker برای خروج، order ID و PnL قابل استفاده نمی‌داد، کلید خروج همیشه `SYMBOL_None` ساخته
می‌شد. در نتیجه خروج نامعلوم بعدی همان نماد در همان اجرای برنامه اشتباهاً تکراری فرض و نادیده گرفته
می‌شد. اکنون هر transition مستقلِ باز به بسته یک شناسه ترتیبی مستقل دارد.

## Scope

- Keep exchange order IDs as the primary idempotency identity.
- Assign a process-local sequence only when the closing order ID is unavailable.
- Preserve existing cooldown and outcome-classification policy unchanged.

## Verification

`pytest -q tests/unit/test_b4_broker_reconciliation.py -q`

Result: 10 passed, including two independent unknown closures of the same symbol.

## Verdict

`KEEP — VERIFIED RECONCILIATION IDEMPOTENCY FIX`.

This does not claim that `PnL=None` is a loss or profit, and it does not change how unknown outcomes
affect cooldown. No runtime, broker, account, or production setting was changed.
