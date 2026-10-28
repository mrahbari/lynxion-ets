# TASK-0385 — Lead-B quarter-hour replication preregistration

## خلاصه ساده فارسی

قبل از مشاهده نتیجه Lead B، نمونه و قواعد آزمون قفل شدند. اولین روز کامل هر ماه در سال‌های ۲۰۲۴
و ۲۰۲۵ به‌صورت مکانیکی انتخاب شد: ۲۴ روز در چهار fold شش‌روزه. پنجره اول ۱۰ثانیه ربع‌ساعت، دو
کنترل داخل همان بلوک و افق‌های ۴، ۸ و ۱۲ ساعت دیگر قابل تغییر نیستند. این فقط replication علمی
است؛ حتی نتیجه مثبت هم مستقیماً strategy یا edge محسوب نمی‌شود.

## Evidence

- Selection script reads only manifest completeness and raw-file existence, not flow or returns.
- Exactly 24 dates are frozen, six in each chronological fold.
- Opening/control windows, variables, horizons, integrity floor, rejection rules, and promotion to
  an economic preregistration are all frozen in the protocol.
- No archive outcome was opened by this task.
- Focused test: 1 passed.
- Verdict: `PREREGISTERED — READY TO RUN MINIMAL REPLICATION`.
- C-35 passes integrity with 21,066 candles, 3,678 prospective records, 114 funding records, 672
  receipts, and 154 no-signal decisions; economics remain sealed.
- C-33 is healthy with one active public session and 1,166 eligible completed buckets.
- C-11 is not due before its eight-hour interval and remains unchanged.

## Next

Implement the one disposable replication script within the frozen budget, run integrity first, and
only then evaluate the predeclared relationships. Reject immediately if integrity or replication
gates fail.
