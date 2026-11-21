# TASK-0450 — Remove Embedded Telegram Credential

## Scope

Remove the exposed Telegram bot credential from current tracked source, configuration defaults,
and test fixtures. Preserve environment-based configuration and fail closed when required values
are absent.

## Changes

- Replaced embedded bot-token and token-bearing update-URL defaults with empty values.
- Kept runtime configuration available through `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and the
  optional `TELEGRAM_BOT_UPDATE_URL` environment variables.
- Added regression coverage proving the notification service has no credential fallback.
- Redacted Telegram credential fields from settings golden comparisons so local environment values
  cannot enter snapshots or test output.

## Verification

- Tracked Python, environment, YAML, and JSON files contain no token-shaped Telegram credential.
- Telegram notification and settings regressions: 13 passed.
- `git diff --check`: clean.

## Boundary

This task removes the credential from the current repository state. It does not revoke the exposed
token, purge Git history, edit local secrets, contact Telegram, or restart the trading runtime.
The operator must revoke and reissue the token through BotFather before notifications are trusted.

## خلاصه فارسی ساده

توکن تلگرام از کد، تنظیمات پیش‌فرض و فایل تست حذف شد. از این پس توکن فقط باید از متغیر محیطی
خوانده شود و نبودن آن باعث توقف امن ارسال اعلان می‌شود. چون توکن قبلی قبلاً داخل مخزن بوده، حذف
کد به‌تنهایی کافی نیست و آن توکن باید در BotFather باطل و توکن جدید جایگزین شود.
