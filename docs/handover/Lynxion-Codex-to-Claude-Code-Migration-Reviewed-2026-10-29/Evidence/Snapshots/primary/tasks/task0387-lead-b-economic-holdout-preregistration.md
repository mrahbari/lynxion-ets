# TASK-0387 — Lead-B economic holdout preregistration

## خلاصه ساده فارسی

قبل از دیدن نتیجه‌های ۲۰۲۶، آزمون اقتصادی Lead B قفل شد. روزی دو معامله غیرهم‌پوشان در ساعت
۰۰ و ۱۲ UTC، ورود فقط بعد از پایان ۱۰ ثانیه مشاهده و خروج ۱۲ ساعت بعد بررسی خواهد شد. هزینه
واقع‌گرایانه ۰٫۳۰٪، هزینه فشار ۰٫۵۰٪ و funding واقعی محاسبه می‌شوند. اگر سود خالص در همه گیت‌های
زمانی، جهت و هزینه پایدار نباشد، سرنخ رد می‌شود و با تغییر تنظیمات نجات داده نمی‌شود.

## Evidence boundary

- TASK-0386 used only a 2024–2025 mechanically sampled replication set.
- The frozen economic holdout is `2026-01-01..2026-08-28`.
- Manifest metadata confirms 240 retained complete-day entries without reading Lead-B outcomes.
- Exactly 480 scheduled non-overlapping trades are expected before integrity exclusions.
- The raw source manifest and existing point-in-time BTCUSDT funding file are hash-frozen.
- No production strategy, broker route, order, account, risk setting, or runtime was touched.

## Acceptance

- Protocol and companion manifest exist before evaluator implementation.
- Observation, entry, exit, direction, costs, funding, folds, clustering, integrity, KEEP, and
  REJECT rules are explicit.
- A positive statistical association alone cannot pass; net expectancy, confidence, PF, temporal
  and clock-phase breadth, side concentration, stress cost, and drawdown must all pass.
- Status: `FROZEN_BEFORE_OUTCOMES`.

## Next

Implement the single disposable evaluator and focused tests. Run integrity before economics. Return
`INVALID_DATA`, `REJECT_ECONOMIC_EDGE`, or `KEEP_FOR_PROSPECTIVE_CONFIRMATION` exactly as frozen.
