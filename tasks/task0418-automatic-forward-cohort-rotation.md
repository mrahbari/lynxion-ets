# TASK-0418 — Automatic forward-cohort rotation

## خلاصه ساده فارسی

اجرای پلتفرم دوباره فقط با `./lynxion` انجام می‌شود. اگر cohort پیش‌فرض متعلق به commit قدیمی باشد،
launcher بدون حذف یا مخلوط‌کردن داده‌های قبلی یک cohort جدید با نام commit فعلی انتخاب می‌کند. دیگر
لازم نیست کاربر متغیر `LYNXION_FORWARD_EXIT_ROOT_OVERRIDE` را برای هر restart دستی وارد کند.

## Safety contract

- Same-commit default cohorts continue with their frozen run identity and boundary.
- A commit-mismatched default cohort rotates to `cohorts/auto-<first 12 HEAD characters>`.
- An explicit operator override never auto-rotates and still fails closed on commit mismatch.
- Malformed manifests and non-empty roots without activation still fail closed.
- Previous cohort files are neither changed nor imported.
- Duplicate-runner rejection still occurs before cohort resolution or runtime startup.

## Verification

- Resolver regression proves default mismatch selects a new HEAD-scoped empty root while preserving
  the old manifest.
- Wrapper integration regression proves plain `./lynxion` supplies the rotated root and current
  commit to the runtime.
- Existing explicit-override mismatch regression continues to prove fail-closed behavior.
- Launcher syntax validation and ten focused launcher/leverage tests pass.

## Verdict

`KEEP — SINGLE-COMMAND LAUNCH RESTORED — SAFETY BOUNDARY PRESERVED`.

The currently running old process, if any, must still be stopped once so the new launcher and the
TASK-0416 historical-data fix load into memory. Thereafter normal restarts require only `./lynxion`.
