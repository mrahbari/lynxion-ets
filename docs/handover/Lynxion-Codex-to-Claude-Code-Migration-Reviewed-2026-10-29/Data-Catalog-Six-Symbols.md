# Six-symbol data catalog / کاتالوگ داده‌های شش سیمبل

Recorded UTC: 2026-10-28T22:54:46.446569+00:00. Local review date: 2026-10-29 Europe/Stockholm.
Core panel / شش سیمبل اصلی: **BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, ADAUSDT, XRPUSDT**.

Raw/normalized market datasets remain at their existing absolute paths. They are NOT inside this documentation ZIP.
فایل‌های اصلی داده داخل ZIP مستندات نیستند؛ در مسیرهای مطلق زیر باقی‌اند. کپی مستندات به ماشین دیگر به‌تنهایی داده را منتقل نمی‌کند.
The machine-readable [catalog](Evidence/Data-Catalog.json) records each selected file's path, bytes, byte SHA-256, manifest, declared hash scope, matching result, schema, coverage and limitations.

## C06 — principal reusable six-symbol M15 candles

Root: [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c06/binance_futures_15m](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c06/binance_futures_15m).
Files are `<SYMBOL>.csv`; manifest source is Binance USD-M `/fapi/v1/klines`.
Actual timestamp/count scan: 128,352 rows each, 770,112 in total. All six source-byte hashes matched.
All timestamps are UTC candle **open**, epoch seconds. A 15m candle is available only after open+900s; the final bar cannot be used before 2026-08-30T00:00:00Z.
این مجموعه قبلاً برای توسعه دیده شده است؛ بازار کامل تاریخی، holdout مستقل و MTF مبتنی بر دفتر سفارش نیست.

| Symbol | Rows | First bar open UTC | Last bar open UTC | File SHA-256 |
|---|---:|---|---|---|
| BTCUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb` |
| ETHUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843` |
| SOLUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382` |
| BNBUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0` |
| ADAUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a` |
| XRPUSDT | 128,352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | `89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57` |

## Other existing datasets / دیگر داده‌های موجود

| Dataset | Existing local manifest | Scope / limits |
|---|---|---|
| C06_M15_CORE_SIX | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c06/binance_futures_15m/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c06/binance_futures_15m/manifest.json) | 15m OHLCV; UTC bar-open seconds; completed-bar availability is open+15m; already development-opened |
| C09_M15_OLDER_SIX | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c09/binance_futures_15m/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c09/binance_futures_15m/manifest.json) | Older OHLCV era, per-symbol start differs; already outcome-opened, not fresh OOS |
| TAKER_FLOW_M15_CORE_SIX | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/taker_flow/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/taker_flow/manifest.json) | Observed completed-kline trade/quote aggregates; not event-time CVD or L2/quotes |
| BOOKDEPTH_BANDS_CORE_SIX | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/bookdepth/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/bookdepth/manifest.json) | Observed aggregated depth/notional in +/-1..5 percent bands; not price-level L2/BBO or a maker queue; missing buckets retained |
| OI_METRICS_CORE_SIX | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/oi_metrics/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/oi_metrics/manifest.json) | Observed OI/ratio metrics; per-symbol starts/gaps/missing ratios differ; not order book imbalance |
| C10_FUNDING_OLDER_BTC_ETH | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c10/funding/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c10/funding/manifest.json) | Funding settlements, BTC/ETH only, 2020-2022 requested; no guarantee of 2024 cost coverage |
| C12_FUNDING_OLDER_ADA_BNB_XRP | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c12/funding/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c12/funding/manifest.json) | Funding settlements for ADA/BNB/XRP, older requested era |
| C13_FUNDING_NEWER_ADA_BNB_XRP | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c13/funding/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c13/funding/manifest.json) | Funding settlements for ADA/BNB/XRP, newer era; do not assume all six symbols covered |
| C15_SECONDARY_FIVE | [/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c15/binance_futures_15m/manifest.json](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c15/binance_futures_15m/manifest.json) | Different selected five-symbol cohort, not the core six and not a replacement universe |

| Dataset | Symbol | Rows | First source time UTC | Last source time UTC | Reported missing intervals | Ratio-missing rows |
|---|---|---:|---|---|---:|---:|
| C06_M15_CORE_SIX | ADAUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C06_M15_CORE_SIX | BNBUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C06_M15_CORE_SIX | BTCUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C06_M15_CORE_SIX | ETHUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C06_M15_CORE_SIX | SOLUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C06_M15_CORE_SIX | XRPUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C09_M15_OLDER_SIX | ADAUSDT | 102304 | 2020-01-31T08:00:00+00:00 | 2022-12-31T23:45:00+00:00 | 0 | None |
| C09_M15_OLDER_SIX | BNBUSDT | 101344 | 2020-02-10T08:00:00+00:00 | 2022-12-31T23:45:00+00:00 | 0 | None |
| C09_M15_OLDER_SIX | BTCUSDT | 105216 | 2020-01-01T00:00:00+00:00 | 2022-12-31T23:45:00+00:00 | 0 | None |
| C09_M15_OLDER_SIX | ETHUSDT | 105216 | 2020-01-01T00:00:00+00:00 | 2022-12-31T23:45:00+00:00 | 0 | None |
| C09_M15_OLDER_SIX | SOLUSDT | 80516 | 2020-09-14T07:00:00+00:00 | 2022-12-31T23:45:00+00:00 | 0 | None |
| C09_M15_OLDER_SIX | XRPUSDT | 104703 | 2020-01-06T08:15:00+00:00 | 2022-12-31T23:45:00+00:00 | 0 | None |
| TAKER_FLOW_M15_CORE_SIX | ADAUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| TAKER_FLOW_M15_CORE_SIX | BNBUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| TAKER_FLOW_M15_CORE_SIX | BTCUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| TAKER_FLOW_M15_CORE_SIX | ETHUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| TAKER_FLOW_M15_CORE_SIX | SOLUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| TAKER_FLOW_M15_CORE_SIX | XRPUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| BOOKDEPTH_BANDS_CORE_SIX | ADAUSDT | 381549 | 2023-01-01T00:09:31+00:00 | 2026-08-29T23:59:31+00:00 | 3506 | None |
| BOOKDEPTH_BANDS_CORE_SIX | BNBUSDT | 381550 | 2023-01-01T00:09:31+00:00 | 2026-08-29T23:59:31+00:00 | 3505 | None |
| BOOKDEPTH_BANDS_CORE_SIX | BTCUSDT | 381550 | 2023-01-01T00:09:31+00:00 | 2026-08-29T23:59:31+00:00 | 3505 | None |
| BOOKDEPTH_BANDS_CORE_SIX | ETHUSDT | 381838 | 2023-01-01T00:09:31+00:00 | 2026-08-29T23:59:31+00:00 | 3217 | None |
| BOOKDEPTH_BANDS_CORE_SIX | SOLUSDT | 380974 | 2023-01-01T00:09:31+00:00 | 2026-08-29T23:59:31+00:00 | 4081 | None |
| BOOKDEPTH_BANDS_CORE_SIX | XRPUSDT | 381261 | 2023-01-01T00:09:31+00:00 | 2026-08-29T23:59:31+00:00 | 3794 | None |
| OI_METRICS_CORE_SIX | ADAUSDT | 498961 | 2021-12-01T00:00:00+00:00 | 2026-08-29T23:55:00+00:00 | 143 | 92248 |
| OI_METRICS_CORE_SIX | BNBUSDT | 498961 | 2021-12-01T00:00:00+00:00 | 2026-08-29T23:55:00+00:00 | 144 | 92242 |
| OI_METRICS_CORE_SIX | BTCUSDT | 629795 | 2020-09-01T00:00:00+00:00 | 2026-08-29T23:55:00+00:00 | 637 | 92292 |
| OI_METRICS_CORE_SIX | ETHUSDT | 498961 | 2021-12-01T00:00:00+00:00 | 2026-08-29T23:55:00+00:00 | 143 | 92241 |
| OI_METRICS_CORE_SIX | SOLUSDT | 498944 | 2021-12-01T00:00:00+00:00 | 2026-08-29T23:55:00+00:00 | 161 | 92243 |
| OI_METRICS_CORE_SIX | XRPUSDT | 498960 | 2021-12-01T00:00:00+00:00 | 2026-08-29T23:55:00+00:00 | 144 | 91957 |
| C10_FUNDING_OLDER_BTC_ETH | BTCUSDT | 3288 | 2020-01-01T00:00:00+00:00 | 2022-12-31T16:00:00+00:00 | None | None |
| C10_FUNDING_OLDER_BTC_ETH | ETHUSDT | 3288 | 2020-01-01T00:00:00+00:00 | 2022-12-31T16:00:00+00:00 | None | None |
| C12_FUNDING_OLDER_ADA_BNB_XRP | ADAUSDT | 3232 | 2020-01-19T16:00:00+00:00 | 2022-12-31T16:00:00+00:00 | None | None |
| C12_FUNDING_OLDER_ADA_BNB_XRP | BNBUSDT | 3167 | 2020-02-10T08:00:00+00:00 | 2022-12-31T16:00:00+00:00 | None | None |
| C12_FUNDING_OLDER_ADA_BNB_XRP | XRPUSDT | 3272 | 2020-01-06T08:00:00+00:00 | 2022-12-31T16:00:00+00:00 | None | None |
| C13_FUNDING_NEWER_ADA_BNB_XRP | ADAUSDT | 4011 | 2023-01-01T00:00:00+00:00 | 2026-08-29T16:00:00+00:00 | None | None |
| C13_FUNDING_NEWER_ADA_BNB_XRP | BNBUSDT | 4011 | 2023-01-01T00:00:00+00:00 | 2026-08-29T16:00:00+00:00 | None | None |
| C13_FUNDING_NEWER_ADA_BNB_XRP | XRPUSDT | 4011 | 2023-01-01T00:00:00+00:00 | 2026-08-29T16:00:00+00:00 | None | None |
| C15_SECONDARY_FIVE | AVAXUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C15_SECONDARY_FIVE | DOGEUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C15_SECONDARY_FIVE | DOTUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C15_SECONDARY_FIVE | LINKUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |
| C15_SECONDARY_FIVE | LTCUSDT | 128352 | 2023-01-01T00:00:00+00:00 | 2026-08-29T23:45:00+00:00 | 0 | None |

`None` means no value was supplied for that field in the inspected manifest; it is not zero or a clean-data guarantee.
Counts/gaps above are manifest-reported unless an explicit `actual_*` field says otherwise. C06 actual timestamp/count scan, all selected file bytes and all 18 legacy canonical row digests were checked in this review. Full acquisition/source lineage or scientific eligibility was not recreated.

## Hash scopes — important / تفاوت مهم دامنهٔ هش

For `taker_flow`, `bookdepth`, `oi_metrics`, the legacy digest is **canonical CSV data rows, comma joined, LF, no header**. It is neither SHA-256 of gzip bytes nor the full decompressed CSV (CSV header/line endings differ). All 18 such data files matched their declared canonical-row digest. The catalog separately records `actual_file_sha256` for copying bytes.
هش manifest این ۱۸ فایل را با هش خود gzip مقایسه نکنید؛ اختلاف این دو به‌تنهایی خرابی داده نیست. هر دو دامنه جداگانه ثبت شده‌اند. الگوریتم اصلی در اسکریپت‌های snapshot موجود است:

- [scripts/fetch_binance_taker_flow_panel.py](Evidence/Snapshots/primary/scripts/fetch_binance_taker_flow_panel.py)
- [scripts/fetch_binance_bookdepth_panel.py](Evidence/Snapshots/primary/scripts/fetch_binance_bookdepth_panel.py)
- [scripts/fetch_binance_oi_metrics_panel.py](Evidence/Snapshots/primary/scripts/fetch_binance_oi_metrics_panel.py)

```python
import csv, gzip, hashlib
digest = hashlib.sha256()
with gzip.open(path, 'rt', newline='') as stream:
    reader = csv.reader(stream)
    next(reader)  # skip header
    for row in reader:
        digest.update((','.join(row) + '\n').encode())
```

## Interpret the panels correctly / حدود معنای پنل‌ها

- `taker_flow`: M15 kline quote volume / trade count / taker-buy quote volume. It is not an event tape, measured bid/ask, price-level L2 or reconstructible whole-venue CVD.
- `bookdepth`: aggregate ±1…5 percent depth/notional bands; last complete observed snapshot per 5m bucket, gaps retained. It is not price-level L2, best quotes, queue position or a truthful maker-fill model. C18/C19 are already rejected studies; no rescue tuning on their opened cohorts.
- `oi_metrics`: open interest and ratios; OI is not order-book imbalance. Missing ratios and buckets are real limits. C16/C17's tested mechanisms were net negative.
- `C09`: same six symbols, older requested 2020–2022; actual starts differ, as table records. Do not assume all began 2020-01-01.
- `C15`: AVAXUSDT, DOGEUSDT, DOTUSDT, LINKUSDT, LTCUSDT are a **different five-symbol cohort**, not replacement names for the core six.
- Inspected funding manifests cover older BTC/ETH and older/newer ADA/BNB/XRP. They do not establish SOL or BTC-2024 funding coverage. Locate and qualify any other already-existing evidence before economics; do not silently use zero or assume none exists elsewhere.
- هر شش نماد از بازار انتخاب شده‌اند؛ عضویت تاریخی کامل، نمادهای حذف‌شده، receipt معتبر و OOS مستقل با این فایل‌ها اثبات نشده‌اند.

## Existing micro candles / کندل‌های micro موجود

Correct root: `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/history/micro`; `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/history/micro` does not exist.
There are five symbols at each of `1m/` and `5m/`: BTC-USDT, ETH-USDT, SOL-USDT, HYPE-USDT, WLD-USDT.
Only BTC/ETH/SOL overlap the core six. Each 1m file has 64,500 rows; each 5m file 12,900 rows. Exact hashes and raw start/end seconds are in the catalog. These are OHLCV/trade aggregates, not BBO/OBI/L2 proof. Historical lineage remains unqualified.
تعداد سه در گزارش قبلی به هم‌پوشانی با شش نماد اشاره داشت، نه کل فایل‌های این پوشه.

## Existing BTC aggregate-trade archive

`/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/btc_aggtrades/raw`; manifest `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/btc_aggtrades/manifest.json`.
Manifest reports 972 days, 2024-01-01…2026-08-29, and a 93,312-row normalized M15 file. This review hashed/inspected its manifest; it did not reread/export every raw daily archive or newly certify every event. BTC-only trades cannot supply absent BBO/L2 or prove historical receipt clocks.

## New observed top-five/trade sample — BTC only / نمونهٔ تازه فقط BTC است

Root: `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/epic01_mtf_maker/qualification_2026-10-28`. Fixed development unit: **BTCUSDT, 2024-01-01 UTC**, Tardis public first-of-month samples, Binance futures venue.
This is distinct from the six-symbol candle/aggregate panels. No six-symbol observed full-MTF panel is claimed.

| Kind | Exact raw filename | Bytes | File SHA-256 |
|---|---|---:|---|
| book_snapshot_5 | `binance-futures_book_snapshot_5_2024-01-01_BTCUSDT.csv.gz` | 22,782,992 | `e777c8ffecb6106aa029be30b4606fdc7409863e6f34b677d550b5855aa289ab` |
| trades | `binance-futures_trades_2024-01-01_BTCUSDT.csv.gz` | 20,848,659 | `8387c9d605f986bb6bde754735f5f9c2440ec76908f0d143af1b9282cefe981a` |

Stored under `raw/`; 43,631,651 compressed bytes total. Receipts/qualification snapshots are packaged; raw files remain local.
Derived file: `/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/epic01_mtf_maker/qualification_2026-10-28/derived/observed_mtf.jsonl`; SHA-256 `ba8305a23447af1c38eff4566a91341765bba2d09336864b00488a730d1600d9`.
1,201,744 observed book rows / 2,197,331 trade rows. 1,440 fresh 1m quotes and 278 accepted 5m OBI/delta boundaries out of 288; 52 late trades invalidate 10 buckets. Maximum observed book-receive gap: 1,831,042 microseconds.
Availability = max(exchange timestamp, vendor local timestamp), both microseconds. Current download receipt is not historical market receipt. Vendor-normalized/reconstructed top-five is not raw exchange queue, and CSV has no disconnect messages. The one selected day is already a development/composition unit, not untouched OOS or established Edge.
نمونه فقط شاهد کیفیت ساختاری و مکانیسم اجراست؛ هنوز baseline اقتصادیِ استراتژی، خروج/فاندینگ کامل یا اثبات سودآوری نیست.

## Input eligibility / صلاحیت استفاده

Current EPIC auditor checked 5,158 supplied inputs: 5,150 history inventory files + six C06 + two observed raw sample files. All 5,158 hashes matched. 5,150 remain unqualified; eight are development-only. **Zero independent validation, zero independent holdout, zero economic baseline admitted**.
That eligibility inventory does not enumerate every selected asset in this wider migration catalog. All 43 selected panel files and two new observed raw files were separately hash-checked here; their inclusion is navigation/integrity evidence, not new scientific admission.
Keep prior cohorts and source definitions frozen. Never relabel synthetic values as observed or already-opened development data as untouched OOS.
