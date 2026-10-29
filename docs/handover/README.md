# Lynxion — handover packages

Latest reviewed migration: **29 October 2026 Europe/Stockholm**. Source evidence was
captured 28 October 22:48–22:55 UTC at primary `8e96631` / offline main `1599af9`. This is a
documentation package; current operational state must still be checked in the actual checkouts.

- [گزارش جامع فارسی](Lynxion-Codex-to-Claude-Code-Migration-Reviewed-2026-10-29/Lynxion-Claude-Code-Handover-Persian-Reviewed-2026-10-29.md)
- [Comprehensive English handover](Lynxion-Codex-to-Claude-Code-Migration-Reviewed-2026-10-29/Lynxion-Claude-Code-Handover-English-Reviewed-2026-10-29.md)
- [Six-symbol data catalog / کاتالوگ شش سیمبل](Lynxion-Codex-to-Claude-Code-Migration-Reviewed-2026-10-29/Data-Catalog-Six-Symbols.md)
- [Claude Code: exact continuation task](Lynxion-Codex-to-Claude-Code-Migration-Reviewed-2026-10-29/Claude-Code-Start-Here.md)
- [Reviewed ZIP](Lynxion-Codex-to-Claude-Code-Migration-Reviewed-2026-10-29.zip) and [SHA256](Lynxion-Codex-to-Claude-Code-Migration-Reviewed-2026-10-29.zip.sha256)

Core six: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, ADAUSDT, XRPUSDT. Existing raw/normalized
data remain in their catalogued local directories, outside the documentation ZIP.
The BTC-only observed top-five/trade sample is separately identified. All 30 original
EPIC dispositions and R01–R26, actual remaining component work and P0 gates are included.
EPIC has 9 accepted / 21 withdrawn / 0 active TODO; original full V1 remains undelivered/NO-GO.
No runner recovery, Edge or sole-owner transfer follows from exporting documentation.

Current project navigation: [status and blockers](../LYNXION_CURRENT_STATUS_AND_BLOCKERS.md).
The hourly Codex automation remained ACTIVE at capture; this package does not pause
it or authorize competing writers/launchers. Follow the human's explicit ownership instruction.

## Immutable historical package

The [26 October migration directory](Lynxion-Codex-to-Claude-Code-Migration-2026-10-26)
and [original ZIP](Lynxion-Codex-to-Claude-Code-Migration-2026-10-26.zip) remain byte-identical
dated snapshots of primary `958dbd7` / main `0649178`. Their evidence and historical task
records are retained, including an identical copy of the original ZIP inside the reviewed
package. They are not current instructions, live status or a full code/data backup.

- [Original English report](Lynxion-Codex-to-Claude-Code-Migration-2026-10-26/Lynxion-Comprehensive-Handover-Codex-to-Claude-Code-English.md)
- [گزارش فارسی اصلی](Lynxion-Codex-to-Claude-Code-Migration-2026-10-26/Lynxion-Comprehensive-Handover-Codex-to-Claude-Code-Persian.md)

## Post-snapshot engineering delta — 29 October 2026

Offline main advanced to `7f45c5bc34943f505755f72c3384a61cf0afc795` after the reviewed package was frozen.
A reproduced maker-entry defect allowed unqualified candle/force/manual/market exits,
including a pre-fill candle. The entry-only model now retains position provenance and
refuses those paths before ledger mutation. RED10failures; maker-focused28PASS/1warning;
existing30-file isolated allowlist347PASS/27warnings. Qualified causal exits/funding
and the strategy economic experiment remain unfinished; no deployment or runner recovery.
See the [current main evidence record](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json).
The reviewed ZIP and all its source snapshots remain unchanged dated documentation.

فارسی: پس از بستهٔ frozen، گارد خروج‌های نامعتبر maker در main آفلاین اصلاح شد؛
این تکمیل چرخهٔ خروج/funding، آزمون اقتصادی یا بازیابی رانر نیست. Claude پیش از ادامه
HEAD و شاهد جاری را بررسی کند؛ فایل‌های ZIP قبلی بازنویسی نشده‌اند.

## Further post-snapshot delta — replay/MTF provider boundary

Offline main `e582cb108b634be8a9b258b8fd2a3d13689c9b6f` repairs an additional reproduced input-loss defect.
The actual backtest provider now retains three explicit replay-clock markers and
supplied OBI/CVD/bid/ask rather than erasing them before the strategy adapter.
Eight source lines were added with original CRLF bytes preserved. RED:4FAIL/5PASS;
focused clock/indicator/closed-bar suite29PASS/27warnings; existing30-file isolated
allowlist352PASS/27warnings. Synthetic opposing flow now reaches the actual confirmation
engine and is rejected before optimization; no missing inputs are invented.
This does not qualify observed source-record/hash/as-of binding, actual family economics
or post-fill exit/funding. No real-data probe, economic outcome or deployment was run.
The [current component evidence](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json)
records exact limits. Both frozen migration packages remain unchanged.

فارسی: حذف ناخواستهٔ ساعت replay و ورودی‌های صریح MTF در واسط backtest اصلاح شد.
این اصلاحِ مسیر انتقال داده است؛ هنوز صلاحیت کامل اتصال دادهٔ مشاهده‌شده، خروج/funding،
آزمون اقتصادی یا بازیابی رانر را ثابت نمی‌کند. Claude آخرین HEAD و شاهد جاری را بخواند.
