# Lynxion — handover packages

Latest post-snapshot engineering source: offline main `e4022f0f5e4fde9a6829d522a8cd25711aa4b2e6`; see the frozen component declaration and closed-H1 input receipt below. Frozen reports/ZIPs retain their original capture baselines.

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

## Pinned observed-record binding delta — 29 October 2026

Offline main `7b8bd5c08672614d0ed0e21acb4542e94d9180d3` adds the explicit `ObservedMTFSource` opt-in.
It pins the derived feature bytes by SHA, binds only the exact symbol/closed-bar cut,
retains a per-record witness in accepted intents, and rejects missing/late windows
before synthetic defaults. Unavailable intervals may still warm the OHLC context.
A first changed-code check on the existing actual feature file bound95of96fixed M15
cuts and explicitly excluded one late bucket;96cross-symbol controls rejected.
This used timestamp-only context, not actual C06/setup/strategy replay or economics.
Initial focused50PASS/27warnings; final existing30-file isolated allowlist379PASS/27warnings.
No independent review, raw download/requalification, old maker-probe rerun, broker call
or deployment. Actual-family/parameter/source/model/cost freeze, closed M15/H1 context
composition, post-fill exits/observed funding/full ledger remain required.

- [Current source binder](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/infrastructure/replay/observed_mtf_source.py)
- [Exact evidence and per-cut witnesses](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json)

فارسی: اتصال دقیقِ فایل ویژگی‌های موجود به نماد و زمان پیاده شد؛۹۵ مرز از۹۶مرز ثابت
متصل و یک مرز دیررس رد شد. این فقط کنترل ورودی با زمینهٔ زمانی است، نه نتیجهٔ استراتژی،
سود، تکمیل خروج/funding یا بازیابی رانر. هر دو بستهٔ migration بدون تغییر باقی‌اند.

## Frozen component declaration and closed-H1 receipt — 29 October 2026

Declaration freeze commit `db1064750991dfab5c0f33a97754db3c69493025` preceded the first
new C06 context check. Declaration SHA256:
`cf7f7b74eeb9d9fa7136de72fe25cf0f01301ab6e9d1de45523320f5ca547e06`.
The file records three actual public constructor configs in an explicitly isolated
fallback-settings environment, eighteen source hashes, the fixed BTC/day/grid/warmup
and model/cost/quantity/budget rules. These are not deployed settings or an admitted
economic experiment; source family metadata1h/15m/5m differs from the declared M15
component grid, and that limitation is explicit. Funding/exit/executable-binding
receipts remain gates; no parameter or window was selected using new outcomes.

The pure `closed_mtf_context` helper builds genuine H1 OHLCV from four contiguous
completed M15 candles. Eight new targeted controls PASS/1warning; the prior379-test
selection was not rerun or summed. Post-freeze receipt commit `e4022f0` verifies the
existing BTC C06 SHA and1096warmup+unit rows: every96fixed cut has1000known M15bars and
20complete H1bars, with no forming hour. This was input/context validation only.
Current actual adapter H1/open/volume/config wiring and exit/funding/full ledger remain
unqualified and unfinished; no actual family signal/economic run or deployment.

- [Frozen declaration — preserve bytes](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_COMPONENT_DECLARATION_V1.json)
- [Closed context helper](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/infrastructure/replay/closed_mtf_context.py)
- [Current component evidence/receipt](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json)

فارسی: مشخصات منبع/پارامتر/مدل/هزینه پیش از ارزیابی تازه ثابت شد و ساخت H1 از
کندل‌های کامل M15 روی دادهٔ موجود کنترل شد. این به معنی تکمیل اتصال خانواده‌های واقعی،
خروج/funding، آزمون اقتصادی یا بازیابی رانر نیست. هر دو بستهٔ frozen بدون تغییرند.
