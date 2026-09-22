# TASK-0454 — Phase 3A input and identifiability audit

## خلاصه ساده فارسی

طرح Phase 3A برای پیدا کردن الگوی انتخاب فرصت قبل از سیگنال از نظر روش تحقیق ارزشمند است.
اما داده‌های اصلی PASS-1 و V2 در checkout فعلی پیدا نشدند. بنابراین شمار سیگنال‌ها، انتساب
HMT/TFS، زمان انتشار، فهرست فرصت‌های قابل انتخاب و توان آماری هنوز قابل راستی‌آزمایی نیستند.
اجرای آزمون یا ثبت preregistration قطعی پیش از دریافت این ورودی‌ها معتبر نیست.

## Input audit

- Received: the operator-supplied `LYNXION ETS — PHASE 3A` research mandate as a text attachment.
- Missing from the current checkout and the inspected local attachment tree:
  `research/external_signal_study/` including PASS-1 extracted/reports and the V2
  `temporal_signals.csv`, evidence manifest, review tables, and three reports.
- The prompt's 306/307 signal counts, 100 `1K_EVENT` signals, 62 graphical signals, and final
  HMT/TFS attribution remain unverified claims until the source artifacts are inspected.
- The true contemporaneous eligible symbol universe and exact source venue may remain unknown even
  after V2 is supplied. This must be an explicit identifiability gate before treating non-selected
  symbols as genuine controls.

## Decision

`PHASE3A-0 INPUT BLOCKED — SOURCE ARTIFACTS REQUIRED`.

Accept the methodological direction conditionally. Once the immutable upstream files are present,
hash and audit them, resolve attribution and timestamp semantics, quantify identifiable case and
control counts, then freeze a small primary feature set and power thresholds before market-data
inspection. Do not create Phase 3A research outputs or infer a fingerprint from this prompt alone.

No production, broker, account, frozen cohort, or market-data state changed in this task.
