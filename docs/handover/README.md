# Lynxion — handover packages

Latest post-snapshot engineering source: offline main `3dd39c1` (corrected physical CSV-line witness and strict five-unstarted-only continuation). The admitted fixed development batch is EXECUTING; four profiles have completed, one original input failure is retained and Liquidity stress is RUNNING. Do not restart the batch or reuse spent slots. Latest observed results are in the current status/evidence links below; frozen reports/ZIPs retain their capture baselines.

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
At that receipt, actual adapter H1/open/volume/config wiring and exit/funding/full ledger
were unfinished. The later explicit offline composition below advances input wiring;
production call sites, economic admission and deployment are not certified.

- [Frozen declaration — preserve bytes](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_COMPONENT_DECLARATION_V1.json)
- [Closed context helper](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/infrastructure/replay/closed_mtf_context.py)
- [Current component evidence/receipt](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json)

فارسی: مشخصات منبع/پارامتر/مدل/هزینه پیش از ارزیابی تازه ثابت شد و ساخت H1 از
کندل‌های کامل M15 روی دادهٔ موجود کنترل شد. این به معنی تکمیل اتصال خانواده‌های واقعی،
خروج/funding، آزمون اقتصادی یا بازیابی رانر نیست. هر دو بستهٔ frozen بدون تغییرند.

## Actual-family offline composition and first fixed trace — 29 October 2026

Executable freeze `ce82ad23a48788b75e47c0030b45f8be1ca6b70b` precedes the first fixed
actual-family trace; receipt commit `dd2c1a07da1f33c100c6ee1f4607433fc10a2c46` retains the full per-cut witnesses in
existing component evidence. The new explicit offline wrapper feeds true last20
completed H1 bars to the actual structure calculation and1000closed M15 bars with
actual open/volume and frozen setup config to the original detectors. The provider,
family methods, confirmation and optimizer are real and their18frozen source pins
remain unchanged. Exact recorded constructor/config/runtime hashes are checked.
Temporary instance hooks run only in a credential-empty/network-denied process.
This does not change or certify production/native-timeframe strategy behavior.

The existing30-file isolated selection passed396tests/27warnings; focused18/27 is an
overlapping selection, not additive. First actual BTCUSDT 2024-01-01 trace:288ordered
family/cut rows, seven intents (trend4, breakout2, liquidity1), thirteen flow rejections,
three terminal no-new-entry boundaries and no unexplained source-return/error state.
Each family retained95eligible/1late source masks; no intent was admitted on the late
cut. Trace SHA256 `79c2bc6489af63621a16bd6502aca303cd9f399965ffcf456513dda41194b3b8`.
Seven intents are not seven trades, portfolio admission or Edge. There were no fills,
PnL, optimization, broker calls, runtime launch/deployment or independent review.
The exact selected day is development-only; uniform M15 grid is not native/live equivalence.

Next existing component gate: explicit causal post-fill maker exit/cost, observed
funding and full partial/nonfill/duplicate/exposure/cash/equity ledger reconciliation;
append final model/source/executable admission before economic output. Preserve the
legacy maker-exit refusal and frozen declaration bytes. Do not rerun this completed
trace or create a new baseline/window/search to obtain a different outcome. P0 exact
TRX attribution/startup remains unresolved independently; no journal clearing or start.

- [Offline composition](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/infrastructure/replay/component_family_composition.py)
- [Fixed isolated trace CLI](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/scripts/replay_epic01_component_decisions.py)
- [Execution freeze and complete trace receipt](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json)

فارسی: اتصال آفلاین به محاسبات واقعی سه خانواده و ورودی H1/M15/جریان مشاهده‌شده انجام
و نخستین ردگیری288مرز ثبت شد:7intent و13رد جریان سفارش؛ هیچ fill یا PnL اجرا نشد.
خروج پس ازfill، funding واقعی و تطبیق کامل دفتر مالی هنوز شرط اجرای اقتصادی‌اند.
این پیشرفت بازیابی رانر، اثبات ادج یا تحویل21تعهد لغوشده نیست. فایل‌های دو بستهٔ
frozen، ژورنال و پنج فایل dirty پژوهش بدون تغییر حفظ شدند؛ Claude این index و شاهد
جاری را همراه بستهٔ مورخ بخواند و یک writer واحد نگه دارد.

## Post-fill lifecycle and actual funding input — 29 October 2026

Plan commit `2094e4f` froze the quote/fee/funding rules and one fixed unsigned public
BTC funding-history GET before acquisition. Executable commit `e7717b9f310cf292af90f92a257f92969a6ce40f`
then froze the new explicit offline lifecycle and verification before first actual
funding-binder qualification; receipt commit `5739f28ddb5fe9283706fb2cc6ffdb2ad94a72b2` records that qualification.
All18frozen source files, original declaration bytes and legacy maker-exit refusals
remain unchanged. No offline main source was deployed to primary.

`PostFillMakerLifecycle` calls the original entry ledger/risk/cash/exposure/minimum
admission. Strictly post-fill, fresh executable-side quote batches can trigger modeled
SL/TP with SL-first ambiguity, declared adverse slippage/taker costs, one adverse
snapshot's shared visible-depth budget, partial exits and exact fee/funding allocation.
Cached terminal quotes use only unconsumed depth; insufficient/missing depth blocks.
Funding precedes same-clock fills/exits. Independent cash/inventory/source/mark/partial
identities, terminal flatness, frozen risk parameters and cumulative-peak drawdown are
controlled. This is explicit prototype linear-inventory research accounting, not
exchange margin/liquidation certification or a live execution path.

Final synthetic maker selection81PASS/1warning, including53new parametrized controls;
overlapping existing30-file isolated selection449PASS/27warnings. Earlier74/442are
intermediate selections, not additive or final. A new in-progress terminal fixture
reproduced3FAIL/74PASS before its correction; no production RED or independent review
is claimed. Synthetic market/settlement tests have not opened actual strategy PnL.

The ONE public funding GET returned HTTP200/505bytes. Actual pinned input qualification
accepted exactly BTC's declared2024-01-01 UTC00/08/16 and2024-01-02 UTC00settlements,
with finite signed rates and positive associated marks. Raw SHA256:
`6be2df20102fb31ec797754c69047e31ad3a984d55191676cc9419c0fdf364a9`.
This is now observed ex-post settlement billing data; it is not missing/assumed0, a
historical receive-clock claim, a strategy feature or VST/account funding evidence.
The frozen declaration's historical null funding placeholder is preserved; its new
source evidence is appended in the existing component dossier. Economic admission
remains false. No repeat acquisition or new window is needed.

Data remain outside both documentation ZIPs, under primary:
`data/research/epic01_mtf_maker/qualification_2026-10-28/`:

- `raw/binance_fundingRate_BTCUSDT_2024-01-01_to_2024-01-02.json`
- `funding_acquisition_receipt.json`
- `funding_qualification_receipt.json` (SHA256 `b22dac207e0eecee2184e37602b058a65b24fe8c74948c502f6cf5fc53d9974a`)

Next existing gate: combine actual-family decisions with original-order admission,
arrival/expiry/cancel/nonfill/tape ordering/shared-volume, this post-fill quote/funding
lifecycle and actual adapter discipline callbacks. Qualify complete marking/cash/
partial/exposure/drawdown/terminal receipts and freeze final executable/config/source
admission before any economics. No actual-market exit, maker-tape strategy replay,
fill/PnL/optimization or runtime recovery was run. Existing7intents are still only
intents, and original9accepted/21withdrawn/0activeEPIC obligations remain settled.

- [New explicit offline lifecycle](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/infrastructure/replay/post_fill_maker_lifecycle.py)
- [Current engineering and funding evidence](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json)
- [Official funding history schema](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data#get-funding-rate-history)

فارسی: مسیر صریح خروج پس ازfill، هزینه، funding و تطبیق دفتر مالی با ورودی مصنوعی
کنترل شد؛ نتیجهٔ مجموعهٔ انتخاب‌شده449تست موفق است، نه تأیید سوددهی یا کل سیستم.
چهار رکورد واقعی funding همان واحد ثابت نیز با هش منبع پذیرفته شدند؛ دیگر نباید این
ورودی را مفقود یا صفر فرض کرد. ترکیب کامل با سفارش، tape، لغو/انقضا، عمق مشترک و
وضعیت انضباط خانوادهٔ واقعی هنوز شرط اجرای اقتصادی است. هیچ PnL واقعی یا استقرار و
شروع رانر انجام نشد؛ دو بستهٔ frozen، ژورنال و پنج فایل dirty پژوهش حفظ شده‌اند.

## Fixed development component — execution update, 29 October 2026

Pre-outcome admission `8e2abe4` froze actual family/order/maker/exit/funding/discipline
composition, exact code/runtime/data pins and a maximum SIX attempt slots, after
471selected isolated tests. First trend_following/nominal attempt failed at the raw
quote-row identity gate before any order/fill. Failure/partial evidence was retained
in `c5cfc6b`; it is never relabeled PASS or retried. The new loader had numbered data
records from1 while the frozen qualifier uses physical CSV line2 after the header.
Clocks/prices/latest-asof identity matched at the failed boundary. Correction and
separate admission `3dd39c1` cover ONLY the five original UNSTARTED slots; the failed
slot/old marker are immutable, data/model/quantity/cost/window/source parameters stay
fixed, and maximum6total attempts is unchanged. One row-number test first failed;
focused35PASS/27warnings and final existing30-file480PASS/27warnings passed. No independent review.

Current batch: Trend stress and Breakout nominal/stress completed with no modeled fills
because unchanged original order quantity/exposure admission rejected their orders.
Liquidity nominal completed one original roundtrip split into59entry partials; modeled
cash change is -15.943200836418, total fees0.90065704725 and observed funding credit
0.431550710822098902. These are selected-day MODEL outputs, not broker/account PnL or
Edge. A read-only cross-check on completed outputs matched raw entry/exit rows,
prices/fees/clocks/quantity, funding-before-inventory mutation, cash and running-peak
drawdown. Liquidity stress is still RUNNING at this update, without final metrics.
Do not infer its result or start another process. The original failed nominal Trend
slot has no qualified economic metric; never substitute its stress result.

- [Current Persian status and per-slot table](../LYNXION_CURRENT_STATUS_AND_BLOCKERS.md)
- [Canonical component attempt/evidence ledger](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json)
- [Guarded fixed-budget CLI; spent slots refuse](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/scripts/run_epic01_development_component.py)
- [Full event composition](/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/infrastructure/replay/component_economic_replay.py)

Model results live OUTSIDE frozen ZIPs under primary:
`data/research/epic01_mtf_maker/qualification_2026-10-28/development_component_runs_2026-10-29/`.
Both original once-marker and separate unstarted-continuation marker are retained.
No original EPIC promise reopened, runtime deployment/start, broker access or account
mutation occurred. Bounded local argv-name check at2026-10-29T08:44:19Z found no matching
trading runner and separately identified the offline replay. TRX P0 remains unresolved.

فارسی: ترکیب کامل توسعه‌ای واقعاً وارد اجرا شد؛ یک شکست ورودی حفظ شد و رفع شناسهٔ ردیف،
آن تلاش را تکرار نکرد. چهار جایگاه کامل‌اند؛ Trend/Breakout به سقف ریسک منبع رسیدند و
fill نداشتند. Liquidity nominal یک گردش سفارش با59partial و حدود15.94زیان مدل‌شده داشت؛
آخرین سناریوی stress هنوز در حال اجراست. بودجهٔ6تلاش، تنظیمات/دادهٔ ثابت و همهٔ شواهد
حفظ شده‌اند. این نتیجهٔ حساب واقعی، ادج، تحویل کامل V1 یا بازیابی رانر نیست.
