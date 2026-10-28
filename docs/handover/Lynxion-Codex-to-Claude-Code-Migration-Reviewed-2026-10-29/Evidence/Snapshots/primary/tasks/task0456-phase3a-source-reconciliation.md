# TASK-0456 — Phase 3A source reconciliation

## خلاصه ساده فارسی

اصلاح TASK-0454: فایل‌های PASS-1 و V2 واقعاً وجود دارند، اما زیر
`tasks/1k-event/research/external_signal_study/` قرار گرفته‌اند. شمارش ۳۰۶ سیگنال PASS-1،
۳۰۷ سیگنال V2 و ۱۰۰ سیگنال نسل 1K_EVENT مستقیماً از CSVها تأیید شد. با این حال، انتساب دقیق
HMT/TFS و چند ارجاع گزارش V2 هنوز نیازمند بازبینی منبع خام است؛ این داده‌ها نباید بی‌بررسی
وارد آزمون Phase 3A شوند.

## Read-only evidence

- PASS-1 `signals.csv`: 306 rows; `evidence_index.csv`: 2,051 rows. Their SHA-256 hashes match the
  values recorded in the V2 run manifest.
- V2 `temporal_signals.csv`: 307 rows, including 100 `1K_EVENT`; its SHA-256 matches the V2 run
  manifest. Within those 100: 64 SHORT, 36 LONG, 28 normalized symbols, 11 unknown timeframes,
  and 62 position-box flags.
- All 100 recent rows retain `strategy_label=1K_EVENT`. None has a direct HMT or TFS engine field.
  The operator's later HMT/TFS statement exists in semantic-tag excerpts for `EV-002023` and
  `EV-002024` (both after the associated signal time), supporting retrospective interval-level
  attribution only until raw evidence is checked.
- `manual_review_v2.csv` labels `SIG-000297` and `SIG-000298` as final TFS LDO/SEI signals, but
  those CSV rows are ETH and ZEC from 2026-09-11. The contemporaneous SEI row is `SIG-000301`;
  the alleged earlier LDO signal appears as `LOOUSDT` in `SIG-000300`. Another LDO signal is
  `SIG-000303` on 2026-09-16. This conflict is unresolved.
- V2 narrative reports cite evidence IDs `EV-002075` through `EV-002080`, although the evidence
  manifest ends at `EV-002051`. The apparent HMT/TFS disclosure text is indexed instead under
  `EV-002023`/`EV-002024`. The latest signal is `SIG-000306`/`EV-002051`, not `EV-002047` as
  stated in one profile section.
- Of 100 recent signal rows, 42 link at least one evidence message published after the signal
  timestamp (64 future links). This is normal for follow-up linkage, but the linked evidence and
  derived tags must be filtered by actual availability time before any Phase 3A feature extraction.
- The raw `jan-jul/result.json`, `aug/result.json`, and linked screenshots are absent from the
  inspected `tasks/1k-event` tree. Image-feature cache and derived tables are present. This limits
  independent verification and graphical geometry calibration.
- The subtree is ignored by the repository's `/tasks/` rule and these upstream files are not
  currently tracked by Git. Hashes can identify the present files, but the current commit cannot
  reproduce their bytes on another checkout.

## Decision

`PHASE3A-0 SOURCE LOCATED — ATTRIBUTION AND RAW-PROVENANCE GATES OPEN`.

The research direction remains valid. Before freezing a HMT-specific case/control protocol,
resolve the mismatched signal/evidence references against the original export, define which
signals have direct versus interval-level engine attribution, and decide whether a study without
the raw screenshots can omit the optional geometry family. Preserve PASS-1/V2 bytes unchanged.

No market outcomes, production code, broker paths, or frozen Lynxion cohorts were inspected or
changed for this audit.
