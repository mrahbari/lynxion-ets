# TASK-0444 — Telegram configuration fail-fast and HTML subject safety

## خلاصه ساده فارسی

اگر chat ID تنظیم نبود، سرویس درخواست ناقص را به Telegram می‌فرستاد و فقط خطای مبهم 400 می‌گرفت.
اکنون پیکربندی ناقص پیش از شبکه رد می‌شود. عنوان اعلان HTML نیز escape می‌شود تا کاراکترهای خاص
پیام را خراب نکنند.

## Scope

- Fail locally when bot token or chat ID is absent.
- Escape only the HTML subject wrapper; preserve already-formatted message bodies.
- Add network-free focused regressions.

## Verification

`pytest -q tests/unit/test_telegram_notification_service.py -q`

Result: 2 passed.

## Security approval gate

A credential appears to be embedded in source defaults. It was not copied, displayed, changed, or
used. Removal plus credential rotation affects secrets/security boundaries and therefore requires
explicit operator approval before a separate task.

## Verdict

`KEEP — LOCAL NOTIFICATION CORRECTNESS FIX; SECRET ROTATION BLOCKED ON APPROVAL`.

No network request, notification, broker/account mutation, or runtime restart occurred.
