# Lynxion — مستند بازبینی‌شدهٔ انتقال از Codex به Claude Code

تاریخ محلی بازبینی **2026-10-29 Europe/Stockholm**؛ شواهد وضعیت در UTC روز ۲۸ اکتبر حدود 22:48 تا22:55 ثبت شده‌اند. زمان ساخت: `2026-10-28T23:10:06.137393+00:00`.
این نسخه لایهٔ راهنمای جاری است؛ [ZIP اصلی ۲۶ اکتبر](Historical/Lynxion-Codex-to-Claude-Code-Migration-2026-10-26.zip) بدون تغییر byte حفظ شده است. متن و دستور قدیمی شاهد تاریخ‌دار است، نه فرمان جاری. [نسخهٔ انگلیسی](Lynxion-Claude-Code-Handover-English-Reviewed-2026-10-29.md).

## وضعیت واقعی پیش از شروع Claude

این بسته **مستندات و شواهد** است؛ محصول کامل، backup تمام کد/داده، استقرار یا انتقال خودکار مالکیت انحصاری اجرا نیست. baseline اولیهٔ این بازبینی در primary برابر **8e9663136f85b566bdc1bc6d85e4c6b3037ecaf1** و main آفلاین **1599af9a1932ba25aee252ae76dfa5ad6b050a76** است. کامیتِ مستنداتِ حامل بسته ممکن است بعداً primary را جلو ببرد؛ main به رانر deploy نشده است.

وضعیت EPIC اکنون **CLOSED_PARTIAL_DELIVERY، ۹ PASS، ۲۱ REMOVED_NOT_DELIVERED و صفر TODO فعال** است. آمار ۸ موفق/۱ ناموفق/۲۱ مسدود تاریخی شده، اما پاک نشده است. یک تحویلِ طبقه‌بندی ورودی واقعاً تکمیل شد و ۲۱ تعهد با ثبت عدم تحویل لغو شدند. **Trading V1 کامل تحویل نشده؛ انتشار NO-GO است.** حذف از دامنه رفع مشکل یا انتقال به صف مخفی نیست. قرارداد مستقل دادهٔ مشاهده‌شده/maker/آزمایش توسعه‌ای حفظ شده و ادامه دارد؛ گیت علمی و ایمنی P0 حذف نشده‌اند.

در بررسی محدود پردازش محلی ساعت22:48UTC رانر Python مطابق پیدا نشد. ژورنال هنوز یک `PROTECTION_UNKNOWN` دارد و شروع را مسدود می‌کند. برای تهیهٔ این مستند هیچ تماس تازهٔ بروکر، شروع رانر، سفارش، reset، deploy، تغییر credential یا بهینه‌سازی اقتصادی انجام نشد. PID قدیمی و برچسب FILLED شاهد رانر جاری، fill بروکر، PnL یا حفاظت فعلی نیست.

از [راهنمای شروع Claude](Claude-Code-Start-Here.md)، [کاتالوگ شش سیمبل](Data-Catalog-Six-Symbols.md)، [شاهد وضعیت](Evidence/Current-State.json) و board جاری EPIC/P0 شروع کنید. «۱۱ کار DONE» فقط صف محدود ممیزی قدیمی بود، نه پایان پروژه.

## مسیر کد، داده و مالکیت اجرا

| محل | شاخه / baseline | کاربرد |
|---|---|---|
| `/Users/mojtaba.rahbari/Sites/python/lynxion-ets` | task-00-ground-truth-audit /8e96631 | primary، config/ژورنال/دادهٔ موجود؛ در بررسی تاریخ‌دار رانر مطابق محلی نبود. |
| `/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets` | main /1599af9؛ هنگام ثبت clean | منبع یکپارچهٔ آفلاین Radar/WFO/backtest/maker؛ `.env` ندارد و به primary مستقر نشده است. |
| `/Users/mojtaba.rahbari/.codex/worktrees/lynxion-epic-01-trading-v1/lynxion-ets` | lynx/epic01-trading-v1 /92218ed | منبع inventory قدیمی ۵۱۵۰ فایل، نه آخرین integration. |
| worktreeهای دیگر | [فهرست واقعی Git](Evidence/Git-worktrees.txt) | شواهد تاریخی؛ مجوز اجرای هم‌زمان یا bulk merge نیستند. |

پنج فایل dirty قبلی بدون تغییر و unstaged حفظ شده‌اند: `data/research/c11/prospective_ledger.json` و C35 `candles.jsonl`، `decisions.jsonl`، `funding.jsonl`، `funding_coverage.jsonl`. هش، حجم و mtime در Current-State ثبت است؛ محتوا و ژورنال خام در بسته نیست. reset، حذف یا stage کلی انجام نشود.

heartbeat ساعتی `lynxion-p0-execution-recovery-and-opportunity-radar` هنگام ثبت **ACTIVE** است، در thread `01a0633b-3fbe-70b0-8f07-8d48ba5e3708`. ساخت بسته آن را pause/delete نکرده و اپراتور هنوز انتقال انحصاری اجرا به Claude را صریح اعلام نکرده است. Claude ابتدا وضعیت/منبع/مالکیت را read-only بررسی کند و پیش از تغییر، یک writer/launcher هماهنگ داشته باشد؛ دستور صریح بعدی انسان حاکم است. کار یا نظارت پیوسته بین اجراهای زمان‌بندی‌شده ادعا نشود.

[سیاست اجرای repo](Evidence/Snapshots/primary/AGENTS.md) در صورت وجود snapshot شده است. کار معمولِ محدود و برگشت‌پذیر نیازمند تأیید روتین نیست؛ مرز secret، پول واقعی، تخریب/از‌دست‌رفتن داده، امنیت و تصمیم برگشت‌ناپذیر پابرجاست. برای سبزشدن چک‌لیست گیت علمی/ریسک تضعیف نشود.

## منابع مرجع و رفع تضاد سندهای قدیمی

- [وضعیت جاری پروژه](Evidence/Snapshots/primary/docs/LYNXION_CURRENT_STATUS_AND_BLOCKERS.md).
- [board اصلی EPIC](Evidence/Snapshots/main/docs/engineering/LYNXION_EPIC_01_TRADING_V1.md)، [دلیل تعیین تکلیف](Evidence/Snapshots/main/docs/engineering/LYNXION_EPIC_01_SCOPE_CLOSEOUT.md) و [هر ۳۰ تصمیم قبلی/نهایی](Evidence/Snapshots/main/docs/engineering/evidence/EPIC01_SCOPE_CLOSEOUT.json).
- [handover بازیابی P0](Evidence/Snapshots/main/docs/engineering/POST_PILOT2_EXECUTION_RECOVERY_HANDOVER.md) و [board شواهد P0](Evidence/Snapshots/main/docs/engineering/POST_PILOT2_EXECUTION_RECOVERY_BOARD.md).
- [رجیستری علمی R01–R26](Evidence/Snapshots/main/docs/research/LYNXION_RESEARCH_BACKLOG.md)؛ labelهای collecting آن تاریخی‌اند.
- [قرارداد frozen داده/maker/اقتصاد](Evidence/Snapshots/main/docs/research/EPIC01_MTF_MAKER_ECONOMIC_CONTRACT.md) و [شاهد واقعی داده/مدل](Evidence/Snapshots/main/docs/engineering/evidence/EPIC01_MTF_MAKER_2026-10-28.json).
- [handover Radar](Evidence/Snapshots/main/docs/research/OPPORTUNITY_RADAR_V1_HANDOVER.md) و [قرارداد Radar](Evidence/Snapshots/main/docs/research/OPPORTUNITY_RADAR_V1_CONTRACT.md).
- [فهرست سندهای جاری](Evidence/Current-Document-Index.md)، [همهٔ فایل‌های task](Evidence/Task-Inventory.md)، [manifest snapshot](Evidence/Source-Snapshot-Manifest.json)، [مستثناها و فایل‌های غایب](Evidence/Exclusions-and-Missing.json).

متن قدیمی عمداً حفظ شده است: BLOCKED مربوط به T02-S02 در handover قدیمی Radar، آمار ۸/۱/۲۱ در قرارداد زمان freeze و نیاز به اصلاح callback train_window_N در migration قبلی، دستور جاری نیستند. closeout بعدی و کد واقعی حاکم‌اند: اتصال live لغو شده، callback اصلاح شده و جزء مستقل حفظ شده است.

## P0 — علت فعلیِ روشن‌نشدن رانر و آنچه هنوز معلوم نیست

در snapshot، ۳۰۱۴ رکورد منطقی latest وجود داشت: ۶۳۱ FILLED، ۲۳۱۵ FAILED، ۶۷ CANCELLED و **۱ PROTECTION_UNKNOWN**؛ JSON خراب صفر بود. برچسب terminal اثبات fill/PnL نیست. رکورد نامعلوم دقیق:

```text
order_ref e554207318004a458b6abf16edc3f39d
2026-10-24T05:49:22.655564+00:00 UTC
TRXUSDT SELL 21.0; purpose PROTECTION; requested stop 0.328502
بدون order_id برگشتی و parent entry_order_ref / هویت دقیق client اثبات‌شده
```

snapshot محدود GET تاریخ ۲۶ اکتبر TRX LONG21 با SL0.32654 و TP0.35153 در وضعیت NEW نشان داده است؛ stop متفاوت همان تلاش را تعیین تکلیف نمی‌کند. تاریخچهٔ محدودِ خالی، صفر match و جست‌وجوی متن/زمانِ محدود ثابت نمی‌کنند سفارش رد یا اصلاً ارسال نشده است. provenance تاریخی FET نیز ثابت نشده. جست‌وجوی تمام‌شده با ورودی/فرضیهٔ یکسان تکرار نشود.

**امتناع فعلیِ startup معلوم است:** بازیابی باید با وضعیت نامعلوم block بماند. **علت ناپدیدشدن رانر اولیه ثابت نشده**؛ این دو را یکسان نگیرید. لانچر primary کنترل precheck→spawn دارد و ۱۳ regression آفلاینِ mock شده admission/check-only/spawn/failure را پوشش می‌دهد. اسکریپت قدیمی `/private/tmp/lynxion_detached_testnet_launch.py` معیوب بود و نباید استفاده شود. اجرای جداگانه پس از precheck مسدود، خطا بود؛ CLI درست امتناع کرد. تا ژورنال مسدود است شروع تکرار نشود.

مسیر A: شاهد معتبر request/response/شناسهٔ همان تلاش و سپس disposition پایدارِ بازبینی‌شده با حفظ raw history. مسیر B: فقط با انتخاب و مجوز صریح مستقل، اثبات بازنشستگی/راه‌اندازی محیط واقعاً ایزوله با حفظ epoch نامعلوم قبلی. مجوز کلی به معنی reset حساب/credential، ژورنال خالی در همان حساب یا پاک‌کردن UNKNOWN نیست. flat بودن فعلی هم انتساب تاریخی نمی‌سازد.

تماس بروکر فقط در دامنهٔ تازه و صریح GET محدود؛ سفارش دستی/نوشتن/cancel/replace، پاک‌کردن ژورنال یا cooldown، reset، restart/deploy و پول واقعی مجاز نیست. سیاست ریسک تغییر نکند. Telegram قبلاً getMe401 داده؛ probe بعدی transport_error داشته، پس هویت/تحویل جاری نامعلوم است. token چاپ یا تغییر نشده است.

## کارهای مهندسیِ انجام‌شده — از سند قدیمی دوباره انجام ندهید

جدول commit زیر نام فنیِ بدون ترجمهٔ نتیجه‌ها را حفظ می‌کند؛ شرح فارسی پس از آن آمده است.

| Location | Commit | Completed result / proof limit |
|---|---|---|
| primary | cc78232, 35cef1f | Checked TESTNET launcher; 13 dated offline mocked regressions; blocked recovery prevents Popen and check-only cannot launch. No real spawn in those tests. |
| primary | 70e7f88 | Corrected UTC frozen-study status audit; no local C11/C33/C35 collectors matched, files stale since September 24. No sealed outcomes opened. |
| main | 0649178 and earlier | Explicit historical replay clocks; reject unsupported maker intents; factory/wrapper actual-symbol binding. Offline, not deployed. |
| main | 264e6fe | WFO fails when requested assets are missing/empty instead of silently dropping them. |
| main | 80eaad5 | Actual-symbol training-only optimizer/CV composition; no longer passes train_window_N as a symbol. Window labels may remain report identifiers. |
| main | 6e99742 | Missing metric values/objectives no longer become fabricated 0 / PF1. |
| main | 7eab7ae | Frozen named public-data/observed-MTF/maker/economic qualification contract before this acquisition. |
| main | 62eed43, a4edfb5 | Observed-MTF qualifier, conservative event maker model, actual partial-fill accounting entry seam; subminimum partial handling corrected. |
| main | 930464c | Recorded real source structure/coverage and fixed mechanics probes. Not strategy profit. |
| main | ed87642 | T01-S04 completed by 5,158 per-file hash/eligibility decisions; no independent OOS admitted. |
| main | 1599af9 | Scope closeout: nine accepted bounded deliveries, 21 withdrawn undelivered; no active EPIC queue, original V1 NO-GO. |
| primary | 8995ffe, 8e96631 | Current status/navigation aligned to observed data and actual EPIC closeout. |

اصلاح callback از کلید پنجره به نماد واقعی، training-only CV، رد asset مفقود، جلوگیری از metric ساختگی و ساعت replay انجام شده‌اند؛ دوباره به‌عنوان کار ناتمام مطرح نشوند. maker مشاهده‌شده و درگاه entry حسابداری ایجاد شده‌اند، اما چرخهٔ اقتصادی کامل هنوز تکمیل نیست.

آخرین شاهد ثبت‌شدهٔ suite انتخاب‌شده با credential خالی و شبکهٔ مسدود: **۳۳۷ PASS /۲۷ warning**؛ اعداد ۳۱۴/۳۰۸/۳۰۵/۲۹۰ به انتخاب منبعِ قبلی مربوط‌اند. ۱۳ تست لانچر و ۲۳ PASS/۱ warning مربوط به Radar/ClosedBarSource/ExtremeMover دامنه‌های جدا و تاریخ‌دارند؛ با هم جمع یا گواهی release کلی تلقی نشوند. برای این export تست تجاری تکرار نشده و مرور مستقلِ patchهای آخر ادعا نشده است.

probe واقعی tape دو جهت مستقلِ ازپیش‌ثابت 0.001BTC در00:05UTC بود: یک BUY fill مدل‌شده و هشت partial SELL؛ مجموع ۹ ورودی با هویت quantity/fee/cash کنترل شد. این شاهد مکانیسم شبیه‌سازی‌شده است، نه سفارش بروکر، خروج، funding یا سود استراتژی.

## Radar کجاست و چه تحویل شده است؟

کد آفلاین در `/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets/scripts/opportunity_radar_v1.py` است. شش فایل M15 C06 را validate می‌کند، حرکت ثابت چهارکندلی و رتبهٔ مطلق در **همین cohort مشاهده‌شده** می‌سازد، context H1 بسته را جدا نشان می‌دهد و metadata پژوهشیِ هم-cutoff را اختیاری پیوست می‌کند. خروجی یک سند **JSON دارای rows array** است؛ JSONL فقط ورودی اختیاری setup است. Fusion/StrategyManager زنده import نمی‌شود و سفارش ساخته/ارسال نمی‌شود.

replay شش‌ردیفیِ ثبت‌شده `OBSERVED_IN_PANEL_TRADABILITY_UNKNOWN` با هش `00e2826377d2fcd7cc89a906c37030b11026c6d0bf3f053a8a8fac49823c937d` و replay اختیاری setup با هش `5ee1160bc726e9cde48001177e8d97243b82bc13bbc055a87b7b398c8bf9889d` حفظ شده است. این رتبهٔ توصیفی، signal، top-mover کل بازار تاریخی یا Edge نیست.

اتصال shadow زنده به watcher/screener یعنی T02-S02 اکنون **REMOVED_NOT_DELIVERED** است؛ تحویل نشده و نباید پنهانی به صف برگردد. ۱۴۳ candidate مربوط به detector ساختاری development-only باقی‌اند. snapshot قرارداد/manifest و تمام taskهای تاریخی حفظ شده‌اند. درخواست انتقال مستندات، مجوز cohort تازه، اسکن کل بازار یا Pilot-3 نمی‌سازد.

## دادهٔ جمع‌آوری‌شدهٔ شش سیمبل — حفظ و استفاده شود

شش سیمبل اصلی دقیقاً **BTCUSDT / ETHUSDT / SOLUSDT / BNBUSDT / ADAUSDT / XRPUSDT** هستند. [کاتالوگ دوزبانهٔ داده](Data-Catalog-Six-Symbols.md) و [فهرست ماشینی فایل‌به‌فایل](Evidence/Data-Catalog.json) جزء اصلی handover هستند.

پوشهٔ اصلی C06: `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c06/binance_futures_15m`. شش فایل `<SYMBOL>.csv` هرکدام **۱۲۸٬۳۵۲ ردیف و مجموعاً ۷۷۰٬۱۱۲ ردیف** دارند؛ از 2023-01-01T00:00Z تا زمان بازشدن آخرین کندل 2026-08-29T23:45Z. شمارش و timestamp واقعی و هش byte کنترل شد. زمان دسترس‌پذیری کندلِ بسته open+15m است؛ آخرین کندل پیش از 2026-08-30T00:00Z در دسترس نبوده است.

| Symbol | Rows | First bar open UTC | Last bar open UTC | File SHA-256 |
|---|---:|---|---|---|
| BTCUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb` |
| ETHUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843` |
| SOLUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382` |
| BNBUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0` |
| ADAUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a` |
| XRPUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57` |

پنل قدیمی‌تر C09، taker flow، bookdepth تجمیعیِ باند درصدی، OI/ratio شش سیمبل و funding زیرمجموعه‌ها موجودند. مسیر دقیق فایل/manifest، ابتدا/انتها، شکاف، ستون‌ها و هش‌ها در کاتالوگ آمده است. همهٔ **۴۳ فایل پنل انتخاب‌شده** با دامنهٔ هش اعلام‌شده تطبیق داشتند؛ دو فایل خام مشاهده‌شده هم تطبیق byte داشتند.

در ۱۸ فایل taker_flow/bookdepth/oi_metrics، هش قدیمی مربوط به ردیف دادهٔ CSV با LF و بدون header است؛ هش gzip نیست. هر ۱۸ مورد با همین قرارداد تطبیق داشت. اختلاف دامنه دلیل خرابی یا دانلود دوباره نیست؛ هش byte برای انتقال نیز جدا ثبت شده است.

پوشهٔ `data/history/micro/{1m,5m}` پنج نماد BTC/ETH/SOL/HYPE/WLD در هر تایم‌فریم دارد؛ فقط BTC/ETH/SOL با شش نماد اصلی مشترک‌اند. کندل و trade aggregate شاهد BBO/L2 نیست. آرشیو aggTrades فقط BTC از 2024-01-01 تا 2026-08-29 جداست؛ manifest آن اکنون کنترل شد، نه تک‌تک همهٔ روزهای آرشیو خام.

نمونهٔ تازهٔ دفتر سفارش/معامله **فقط BTCUSDT روز 2024-01-01** است، در `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/epic01_mtf_maker/qualification_2026-10-28`؛ دو فایل عمومی Tardis با مجموع ۴۳٬۶۳۱٬۶۵۱ byte فشرده. ۱۴۴۰ quote تازهٔ یک‌دقیقه‌ای و ۲۷۸ از ۲۸۸ پنجرهٔ پنج‌دقیقه‌ای OBI/delta پذیرفته شدند؛ ۵۲ trade دیررس ده پنجره را حذف می‌کنند. این نمونه MTF مشاهده‌شدهٔ شش نماد، صف کامل صرافی، capture پیوسته یا OOS مستقل نیست. هش derived: `ba8305a23447af1c38eff4566a91341765bba2d09336864b00488a730d1600d9`.

funding باید برای هر نماد/تاریخ اثبات شود؛ manifestهای بررسی‌شدهٔ C10/C12/C13 پوشش BTC-2024 یا SOL را ثابت نمی‌کنند. نبود funding با صفر جایگزین نشود. دادهٔ قبلی برای توسعه دیده شده؛ بازار کامل تاریخی و validation مستقل واجد شرایط نیست. تکمیل T01-S04 به معنی طبقه‌بندی ورودی‌هاست، نه پذیرش اقتصادیِ مثبت.

**دادهٔ خام/normalized داخل ZIP مستندات نیست.** Claude روی همین ماشین باید از مسیر اصلی استفاده کند. برای ماشین دیگر، repo و Git/worktree، داده‌های ignored، دارایی frozen و ژورنال عملیاتی باید جداگانه و تحت مرزهای موجود منتقل شوند؛ Git همهٔ داده‌ها را ندارد. ژورنال خالی جایگزین نشود و `.env` وارد بستهٔ اشتراکی نشود.

## کار ناتمام واقعی در محدودهٔ مستقلِ موجود

این جدول مسیر ادامهٔ تعهدهای موجود است؛ backlog تازه یا احیای ۲۱ تعهد لغوشده نیست. کار مهندسیِ مستقل و مجاز را بدون تأیید روتین ادامه دهید؛ برای گام وابسته به شاهد مفقود، بلاکر دقیق و خروجی لازم را ثبت کنید.

| کار موجود | تحویل واقعی تا اینجا | خروجی باقی‌مانده و شرط پذیرش |
|---|---|---|
| P0 و حقیقت اجرا / R14 | امتناع پایدار، لانچر کنترل‌شده، نقشهٔ شاهد و snapshot محدود و تاریخ‌دار بروکر | انتساب معتبر همان تلاش TRX و تعیین وضعیت پایدارِ بازبینی‌شده؛ یا فقط با انتخاب و مجوز مستقل، بازنشسته‌کردن محیط واقعاً ایزوله. جست‌وجوی تکراریِ بدون فرضیه، پاک‌کردن UNKNOWN یا ژورنال خالی در همان حساب راه‌حل نیست. |
| اتصال MTF مشاهده‌شده | دو فایل عمومی، هش معتبر، quote یک‌دقیقه‌ای و OBI/delta پنج‌دقیقه‌ای با کنترل ساعت | اتصال خانواده‌های واقعی و source-frozen به پنجره‌های مجاز و کندل بستهٔ M15/H1؛ ثبت هش استراتژی/ویژگی/مدل/داده، پارامتر، warmup و trace تصمیم/رد پیش از نتایج اقتصادی. ده پنجرهٔ دیررس با مقدار ساختگی پر نشوند. |
| maker در چرخهٔ واقعی استراتژی | مدل trade-through، probe ثابت روی tape و ورودی `apply_modeled_maker_fill`؛ حسابداری ۹ fill مدل‌شده | اتصال admission واقعی و چرخهٔ پورتفو؛ partial/nonfill/expiry، کارمزد، وجه نقد/equity، exposure و duplicate کنترل شوند. حلقهٔ معمول OHLCV هنوز maker را رد می‌کند؛ maker نباید به market تغییر نام یابد. |
| خروج و هزینهٔ علّی | فرض‌های maker/taker، تأخیر، TTL و participation در قرارداد frozen | خروج و SL/TP فقط پس از fill و با اطلاعات واقعاً در دسترس؛ High/Low قبل از fill برای خروج استفاده نشود. اولویت SL در ابهام، اسلیپیج نامساعد، funding مشاهده‌شده و drawdown از قله تا دره لازم است. funding یا شاهد مفقود صفر نیست. |
| baseline جزء توسعه‌ای واجد شرایط | قرارداد و اجزای داده/مدل موجودند؛ خروجی اقتصادی استراتژی پذیرفته نشده | پس از قبولی ترکیب/ورودی/مدل/هزینه، آزمایش ثابت و تکرارپذیر بدون جست‌وجوی پارامتر با تصمیم‌های واقعی، شمارش رد/nonfill و حسابداری کامل. یک روز انتخابی اثبات Edge یا OOS مستقل نیست. |
| R04–R06 / C11,C33,C35 | پروتکل frozen و وضعیت‌های تاریخ‌دار حفظ شده‌اند | فقط status/metadata تا گیت اصلی sample/breadth/cost. ممیزی نگه‌داشته‌شده پردازش محلی مطابق پیدا نکرد و فایل‌ها از سپتامبر قدیمی‌اند. جمع‌آوریِ جاری فرض نشود، collector جایگزین راه نیفتد و نتایج مهروموم‌شده زودتر باز نشوند. |
| Telegram | getMe401 مستقل و سپس transport_error تاریخ‌دار ثبت است | هویت و تحویل جاری تأیید نشده؛ اپراتور credential درست را تأمین می‌کند. هیچ token چاپ، حدس یا بازنویسی نشود؛ این انتقال پیام آزمایشی نفرستاده است. |

[قرارداد منبع](Evidence/Snapshots/main/docs/research/EPIC01_MTF_MAKER_ECONOMIC_CONTRACT.md): شمارش و ارجاع‌های T01/T04/T05 در زمان freeze تاریخی‌اند؛ تصمیم closeoutِ بعدی برای EPIC اصلی حاکم است. جزء مستقلِ صریحاً حفظ‌شده ادامه دارد؛ جایگزین تحویلِ baseline کامل، Radar زنده، Hyperopt/WFO/OOS یا انتشار نشده است.

## مسیر دستیابی به Edge و شرط توقف ادعای اقتصادی

**هیچ Edge مثبت یا سودآوریِ واجد شرایط اثبات نشده است.** حجم زیاد کندل، شاهد receipt، عضویت کامل بازار تاریخی و holdout دست‌نخورده نمی‌سازد. نتیجهٔ منفی مطالعات قبلی مجوز tuning همان cohort نیست.

1. verdict و پروتکل قبلی را حفظ کنید و واحد مجاز دقیق را مشخص کنید. از دادهٔ شش سیمبل برای نقش توسعه‌ایِ مستندش و از روز مشاهده‌شدهٔ BTC فقط برای جزء محدود استفاده کنید.
2. اول اتصال علّی داده/استراتژی/اجرا/هزینه تکمیل شود: واحد زمان، availability، حذف پنجرهٔ ناقص، جداسازی نماد، حسابداری partial/خروج و معیارِ غیرساختگی با regression هدفمند ثابت شوند.
3. پیش از دیدن نتیجه، نسخهٔ آزمایش، پارامترها، برش و هش داده، هزینه/funding، بودجهٔ ارزیابی و قرارداد گزارش frozen شوند. در واحد ثابت یک‌روزه جست‌وجوی پارامتر ممنوع است.
4. فقط پس از پذیرش، baseline توسعه‌ای با ledger کامل پس از هزینه، failure و nonfill گزارش شود. صفر معامله PF1 نمی‌سازد؛ معیار تعریف‌نشده همان‌طور بماند. این گزارش تعهدِ لغوشدهٔ baseline کامل را احیا نمی‌کند.
5. هر ادعای مستقل بعدی به طرح جداگانهٔ قبل از outcome با OOS زمانی دست‌نخورده، توان آماری، هزینه، کنترل تعدد خانواده/آزمون و breadth/concentration نیاز دارد. بهینه‌سازی WFO فقط training را می‌بیند؛ دادهٔ دیده‌شده holdout تازه نمی‌شود.
6. شکست هر گیت با شاهد دقیق ثبت شود؛ با تغییر نام استراتژی، افزایش تعداد تست یا تغییر معماری سبز اعلام نشود. گیت رانر از نتیجهٔ پژوهش مستقل است.

## هر ۳۰ شناسهٔ EPIC — هیچ FAIL/BLOCKED حذفِ بی‌ردپا نشده است

دستور شما انجام یا خروج از لیست بود. هشت تحویل پذیرفته‌شده حفظ شد؛ T01-S04 با تطبیق و طبقه‌بندی ۵۱۵۸ فایل واقعاً تحویل شد؛ ۲۱ تعهد با ثبت عدم تحویل لغو شدند. FAIL قبلی اصلاح‌شده نام نگرفت. backlog مخفی و حذف گیت ایمنی/علمی رخ نداده؛ دلایل کامل انگلیسی در جدول و فارسی در closeout snapshot موجود است.

| ID | Original scenario | Prior state | Final disposition | Evidence / rationale |
|---|---|---|---|---|
| T01-S01 | Active strategy, watcher, Fusion and Regime composition inventoried | BLOCKED | **REMOVED_NOT_DELIVERED** | Deployed-composition certification withdrawn from this delivery; source inventory is retained but no running active set is certified. |
| T01-S02 | Raw 1m per-symbol coverage and integrity quantified | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T01-S03 | Processed MTF per-symbol coverage and resampling lineage quantified | BLOCKED | **REMOVED_NOT_DELIVERED** | Full historical processed-to-raw lineage cannot be established from the supplied provenance; no lineage will be invented or reconstructed retroactively as observed evidence. |
| T01-S04 | Development, validation and holdout eligibility classified | BLOCKED | **PASS** | Completed per-file eligibility decisions with actual SHA readback for 5158 supplied/current inputs: 5150 unqualified and eight development-only; zero validation/holdout/economic-baseline admissions. Classification completion is not data qualification. |
| T02-S01 | Existing Radar and screener reuse proven | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T02-S02 | Movement observation remains read-only at watcher/screener boundary | BLOCKED | **REMOVED_NOT_DELIVERED** | Live watcher/screener shadow-port delivery is cancelled for this charter; the delivered offline research Radar is retained without claiming live integration. |
| T02-S03 | Regime classification remains separate | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T02-S04 | Causal timestamp, source and quality fields retained | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T02-S05 | Shadow output cannot alter trading selection or routing | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T03-S01 | Watcher name/role mapping verified | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T03-S02 | Signal timestamp and freshness verified | FAIL | **REMOVED_NOT_DELIVERED** | Full historical signal/freshness parity was not accepted; the original FAIL is preserved in the closeout evidence. This scope is withdrawn, not marked fixed or PASS. Explicit replay guards remain mandatory. |
| T03-S03 | Fusion agreement, HOLD and rejection reasons reported | BLOCKED | **REMOVED_NOT_DELIVERED** | Full production/Fusion decision-trace certification is not delivered and is withdrawn from this charter; earlier bounded incident evidence is retained. |
| T03-S04 | Strategy registration, defaults, thresholds and weights verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Deployed registration/default/weight certification is withdrawn; changing live admission to make a checklist green is prohibited. |
| T03-S05 | Symbol isolation, intent suppression and cooldown verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Whole-system symbol/cooldown/admission acceptance is not delivered and is withdrawn; existing duplicate and risk protections remain enforced. |
| T04-S01 | Trend Pullback plan frozen from existing code | BLOCKED | **REMOVED_NOT_DELIVERED** | Requested Trend Pullback semantics are not established by NGTREND_FOLLOW; do not build or rename a new strategy to satisfy an unsupported plan label. |
| T04-S02 | Breakout/Retest plan frozen from existing code | BLOCKED | **REMOVED_NOT_DELIVERED** | Requested Breakout/Retest semantics are not established by NGBREAKOUT; the unsupported plan promise is cancelled rather than invented. |
| T04-S03 | Momentum Scalping plan frozen from existing code | BLOCKED | **REMOVED_NOT_DELIVERED** | NGLS_SWEEP is not the promised Momentum Scalping plan; that plan promise is cancelled without changing existing strategy semantics. |
| T04-S04 | Causal after-cost baseline backtests executed on qualified data | BLOCKED | **REMOVED_NOT_DELIVERED** | The original full three-plan qualified baseline is not delivered and is withdrawn. A selected one-day observed/model component does not satisfy it. The separately authorized bounded component contract is not a substitute PASS. |
| T04-S05 | Counts, expectancy, PF, drawdown, side, duration and rejections reported | BLOCKED | **REMOVED_NOT_DELIVERED** | Full-baseline economic reporting is cancelled with its undelivered baseline; metrics remain NOT_MEASURED, not fabricated zeroes. |
| T05-S01 | Parameter spaces frozen before optimization output | BLOCKED | **REMOVED_NOT_DELIVERED** | Full-plan optimization parameter-space delivery is cancelled because the required full plan/baseline is not being delivered by this charter. |
| T05-S02 | Chronological WFO train/validation/test boundaries verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Full qualified-data WFO acceptance is withdrawn; tested train-only/calendar source corrections remain engineering assets, not completed real-data WFO. |
| T05-S03 | Evaluation budget and after-cost objective recorded | BLOCKED | **REMOVED_NOT_DELIVERED** | Executing an economic optimization budget without the required baseline would be invalid; full-plan search is cancelled, not run to fill a checkbox. |
| T05-S04 | Holdout and overfit verdict explicitly qualified | BLOCKED | **REMOVED_NOT_DELIVERED** | No untouched holdout is admitted; full independent OOS/overfit certification is withdrawn rather than manufacturing independence on opened data. |
| T06-S01 | Signal-to-intent simulated path verified | BLOCKED | **REMOVED_NOT_DELIVERED** | Whole-system signal-to-intent release certification is withdrawn; partial offline mechanism evidence is retained without release promotion. |
| T06-S02 | Duplicate prevention and unknown outcome tested | BLOCKED | **REMOVED_NOT_DELIVERED** | Full duplicate/UNKNOWN/restart release certification is not delivered; withdrawing this task does not clear any journal uncertainty or weaken admission. |
| T06-S03 | Protective-order semantics tested | BLOCKED | **REMOVED_NOT_DELIVERED** | Deployed protective-order certification is not delivered and is withdrawn from this EPIC; authoritative P0 protection requirements remain non-negotiable before startup. |
| T06-S04 | Journal, reconciliation and restart persistence tested | BLOCKED | **REMOVED_NOT_DELIVERED** | Whole-system persistence/reconciliation/restart certification is withdrawn; unresolved exact-attempt P0 evidence remains in its existing safety dossier. |
| T06-S05 | No-lookahead deterministic replay and P0 gate retained | BLOCKED | **REMOVED_NOT_DELIVERED** | Full deterministic/no-lookahead release acceptance is withdrawn; existing causal guards are retained and no VST/live permission is granted. |
| T07-S01 | Existing research IDs linked without verdict overwrite | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |
| T07-S02 | Release report separates correctness, performance, OOS, readiness and Edge | PASS | **PASS** | Previously accepted bounded deliverable retained; no new test or broader certification claimed. |

## تمام R01–R26 — verdict علمی تغییر نکرده است

جدول زیر عین overlay اصلی است: ۱۵ CLOSED_FINAL، چهار ACTIVE_DELIVERABLE، سه BLOCKED_EXTERNAL و چهار RESEARCH_ASSET. این رجیستری علمی با صف لغوشدهٔ EPIC فرق دارد. شمارش‌ها و label جمع‌آوری تاریخ‌دار هستند؛ liveness جاری را اثبات نمی‌کنند. متن کامل canonical و پروتکل‌ها در snapshot و تاریخ اصلی حفظ شده‌اند.

| ID | Preserved scientific status (dated) | Operational disposition | Existing gate / permitted next step | Dependency |
|---|---|---|---|---|
| R01 | `PHASE3A_INCONCLUSIVE_DATA_LIMITED` | `CLOSED_FINAL` | New attributable cohort/preregistration for a different study | External feed; **NO** |
| R02 | `FROZEN_PROSPECTIVE_RESEARCH_LEAD` | `BLOCKED_EXTERNAL` | Complete new sibling feed and valid activation | External feed; **NO** |
| R03 | `COMPRESSION_FORWARD_1_BLOCKED_SIGNAL_FEED`, M3 `NOT_IDENTIFIABLE` | `BLOCKED_EXTERNAL` | Source IDs, cursors, UTC/gap evidence and unopened cohort | External feed; **NO** |
| R04 | C-11 frozen prospective, dated N=5 | `ACTIVE_DELIVERABLE` | Frozen sample/breadth/cost verdict only at its existing gate | Existing collector; status-only audit **YES**, no early verdict |
| R05 | C-33 `PROSPECTIVE_COLLECTING`, dated 1,034/8,640 warmup | `ACTIVE_DELIVERABLE` | Frozen warmup/provenance gate, then its own study decision | Existing collector; status-only audit **YES** |
| R06 | C-35 `TOO_SLOW / COLLECTING`, dated 3/240 outcomes | `ACTIVE_DELIVERABLE` | Frozen sample/cost verdict only at its existing gate | Existing collector; status-only audit **YES** |
| R07 | C-14/C-15 tested momentum rejected | `CLOSED_FINAL` | Distinct mechanism and unopened cohort for any new question | Scientific choice; **NO** |
| R08 | C-16/C-17 OI net negative | `CLOSED_FINAL` | Distinct joint observed panel for any new question | External data/scientific choice; **NO** |
| R09 | Tested aggregate flow/toxicity rejected | `CLOSED_FINAL` | Qualified different source/independent protocol | External data/scientific choice; **NO** |
| R10 | `NO NEW FUNDING-STATE TEST — CONTINUE FROZEN C-11 ONLY` | `CLOSED_FINAL` | No broad-state retest; C-11 is R04 | Scientific choice for new mechanism; **NO** |
| R11 | `LOW_INFORMATION_VALUE — DO_NOT_BUILD` | `CLOSED_FINAL` | None on this study | None; **NO** |
| R12 | C-18/C-19 aggregated depth `REJECT` | `CLOSED_FINAL` | Distinct price-level hypothesis, not band-depth retuning | Scientific choice; **NO** |
| R13 | Lead B `REJECT_ECONOMIC_EDGE` | `CLOSED_FINAL` | None on opened cohort | None; **NO** |
| R14 | Lead A `INSUFFICIENT_PROVENANCE` | `ACTIVE_DELIVERABLE` | Authoritative joined mark, entry/exit fill, venue and timestamp evidence; **not** exit optimization | P0 Execution Recovery/external broker truth; requirements mapping **YES**, Edge test **NO** |
| R15 | Pre-intent `NOT_IDENTIFIABLE` | `CLOSED_FINAL` | New direction semantics would be another study | Scientific/trading decision; **NO** |
| R16 | V1 `PREDICTIVE_NOT_SUPPORTED` | `CLOSED_FINAL` | None on this study | None; **NO** |
| R17 | V2 `V2_DATA_LIMITED` | `CLOSED_FINAL` | Unopened independent cohort for any new study | Scientific choice; **NO** |
| R18 | Historical microstructure feasibility complete | `CLOSED_FINAL` | Separate qualified information/hypothesis required | No new capture authorized; **NO** |
| R19 | Pilot-1 `MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL` | `CLOSED_FINAL` | Immutable measurement evidence | None; **NO** |
| R20 | Sibling forensic mechanism map complete, Edge unknown | `RESEARCH_ASSET` | Full denominator/attribution before economics | External feed; preserve map **YES**, new test **NO** |
| R21 | Phase-6 `PROVISIONAL_ONLY`, zero full promotions | `CLOSED_FINAL` | None on opened screen | Scientific choice for new mechanism; **NO** |
| R22 | `EXTREME_MOVER_DATA_PARTIAL`, contract complete | `RESEARCH_ASSET` | Qualified time-T universe/costs and a separately frozen experiment | External data; causal interface/synthetic tests **YES**, historical ranks **NO** |
| R23 | Public methodology review complete | `RESEARCH_ASSET` | None; use only research discipline | No dependency; **NO** new task |
| R24 | Annotation protocol design complete, inactive | `RESEARCH_ASSET` | Frozen inclusion/window and authorization to activate | New collection/scientific choice; **NO** |
| R25 | Liquidation/OI/OBI reconciliation complete, joint panel absent | `BLOCKED_EXTERNAL` | Observed overlapping panel plus one directional hypothesis | External data/scientific choice; **NO** |
| R26 | Pilot-2 `MICROSTRUCTURE_COLLECTION_PILOT_PARTIAL` | `CLOSED_FINAL` | Immutable measurement evidence, no repeat | None; **NO** |

مطالعهٔ منفی بسته‌شده اینجا باز نمی‌شود. R14 پیش از اقتصاد خروج به حقیقت اجرای معتبر نیاز دارد؛ R02/R03/R25 به شاهد خارجی و تصمیم علمیِ اصلی وابسته‌اند. Pilot-1/Pilot-2 با verdict PARTIAL، cohort frozen و منع تکرار حفظ شده‌اند. واحد عمومی دو فایل استثنای محدود بعدی است؛ مجوز collector آینده‌نگر جایگزین یا سرویس پولی نیست.

## صحت انتقال، پوشش و مواردِ داخل بسته نیست

توسعه را در repo واقعی انجام دهید؛ Evidence/Snapshots کپی مستنداتی و همهٔ dependencyها/checkout اجرایی نیست. بعضی پیوندهای تاریخیِ داخل source به داده/باینری محلیِ خارج از export اشاره دارند؛ این محدودیت اعلام شده است. پیوندهای خود گزارش و index بسته کنترل می‌شوند. manifest، هش source و export و هر redaction را جدا ثبت می‌کند.

ZIP اصلی ۲۶ اکتبر عین byte نگه داشته شد: `cca0039301ab0265d66138c4310e95bf4708542936a4c47e5a8b85a74671678f`؛ هر ۱۴۵۹ entry checksum داخلی تطبیق دارد. آن ZIP شامل ۱۴۵۰ snapshot سند و ۷۰۱ task تاریخی در rootهای قبلی است. baseline958dbd7/0649178 آن برای اجرای جاری قدیمی است. همهٔ Markdownهای جاری primary/main در docs/tasks/research به‌جز handover بازگشتی، هر ۷۰۱ task جاری، evidence جدید، کد انتخاب‌شدهٔ تغییریافته/حیاتی، manifest داده، index و تاریخ Git جدا صادر شده‌اند. [گزارش پوشش](Evidence/Export-Coverage.json).

مستثناها: `.env` و credential، محتوای ژورنال عملیاتی، cohort خصوصی/خام frozen، payload بازار CSV/JSONL/باینری جز evidence صریح inventory/qualification، virtualenv، database، Git objects و runtime log. metadata فایل dirty بدون محتوا ثبت است. raw/normalized داده باید جدا از مسیر اصلی منتقل شود. pattern scan محدودِ secret و redaction در کپیِ سند ثبت شده؛ تضمین کشف تمام secretهای تاریخی نیست. هیچ source اصلی redact یا بازنویسی نشده است.

از پوشهٔ بسته `python3 verify_package.py` فقط byte هر entry manifest را کنترل می‌کند؛ Lynxion import یا داده دریافت نمی‌کند و پردازش رانر شروع نمی‌شود. ZIP فایل SHA256 کنار خود دارد. کنترل hash/لینک/۳۰ شناسه/۲۶ رجیستری/۷۰۱ task/حفظ source، تست artifact است، نه تست تازهٔ استراتژی یا آمادگی runtime.

[دستور شروع و ادامهٔ دقیق Claude](Claude-Code-Start-Here.md) همراه بسته است. در board موجود، تغییر واقعی، تست واقعاً اجراشده، commit، محدودهٔ مرور، محدودیت اثبات و گیت بعدی را بنویسید. پایان صف ۱۱تایی، بسته‌شدن ناقص EPIC یا افزایش تست به معنی پایان کل پروژه نیست.
