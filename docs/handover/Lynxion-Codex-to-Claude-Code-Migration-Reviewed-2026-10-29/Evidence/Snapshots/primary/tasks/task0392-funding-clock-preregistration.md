# TASK-0392 — Funding Settlement market-quality preregistration

## خلاصه ساده فارسی

تست Funding Settlement قبل از دیدن نتیجه قفل شد. پنجره‌های ۴۵دقیقه‌ای قبل و بعد از funding با
وسط واقعی همان چرخه مقایسه می‌شوند و زمان‌های متغیر SOL هم از خود داده خوانده می‌شوند. نتیجه فقط
ارزش اطلاعاتی را می‌سنجد؛ Rescue Ladder و هیچ قانون production تغییر نمی‌کنند.

## Evidence boundary

- Universe, 2023–2026 sample, actual settlement timestamps, midpoint controls, windows, variables,
  clustering, folds, integrity, and verdict gates are frozen.
- Simultaneous symbols share one settlement-time cluster.
- Spread and receive latency remain unavailable, so no executable-quality claim is permitted.
- No outcome values were inspected by this task.
- One static protocol regression test passes.
- Status: `FROZEN_BEFORE_OUTCOMES`.

## Next

Implement one disposable evaluator, run integrity before effects, and return exactly
`INVALID_DATA`, `INFORMATION_VALUE_CONFIRMED`, or `LOW_INFORMATION_VALUE — DO_NOT_BUILD`.
