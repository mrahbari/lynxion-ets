# TASK-0413 — BingX blacklist precedence regression

## خلاصه ساده فارسی

تست کامل نشان داد نماد XMR درست رد می‌شود، اما پیام آن ابتدا «خارج از فهرست مجاز» بود و نه
«بلک‌لیست». ترتیب گیت اصلاح شد تا بلک‌لیست دائمی اولویت داشته باشد و رفتار و گزارش قبلی حفظ شود.

## Correction and validation

- Check the dynamic permanent blacklist before the approved-symbol membership gate.
- No symbol policy, strategy, risk, runtime, or broker state changed.
- Focused regression: 22 tests pass.
- Full suite: 1,223 pass, 1 optional layering test skipped because `import-linter` is unavailable.

## Verdict

`SOURCE_REGRESSION_GREEN — RUNTIME_NOT_VERIFIED`.
