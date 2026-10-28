# Historical candle provenance and coverage qualification

Start `aa1b136`. Read-only offline qualification of the frozen `PRE_INTENT_SIGNAL_STUDY_PREREGISTRATION.md`; no future labels, returns, PnL, strategy changes or data repairs. Primary verdict: **PRE_INTENT_EDGE_MEASUREMENT_NOT_READY**. The smallest decisive blocker is the frozen BTC/ETH 1h cohort's **34 common bars** versus 50 warmup bars and at least 20 distinct UTC days **per symbol**; timestamp/file lineage is also unproved.

## Inventory and lineage

`data/history` contains 654 CSVs in each `processed/{5m,15m,30m,1h,4h,1d}`, 1,227 raw 1m CSVs, 148 raw 1h CSVs, 148 raw 15m/30m CSVs, 149 raw 5m CSVs and five files each in `micro/{1m,5m,15m}`. This is a path inventory, not a claim that all files are valid or independently sourced. The frozen protocol names **only** `processed/1h/BTC-USDT.csv` and `processed/1h/ETH-USDT.csv`. Other intervals/symbols cannot silently replace its cohort.

The processed 1h CSVs have `timestamp,open,high,low,close,volume`, integer 10-digit epochs consistent with seconds, and 3600-second spacing. Code in `infrastructure/data_sync/file_repository_adapter.py` converts raw epochs to UTC, uses pandas `resample('1h')` and writes the resampled index as seconds; such an output would be a **left-labeled interval/open** timestamp and a candidate close would be timestamp + 3600 seconds. But no per-file manifest or recorded producer invocation ties these **particular** processed files to that code or an identified exchange. Current raw 1m BTC/ETH files cover a different August interval; they cannot substantiate the June/July processed rows. `infrastructure/data/resample_engine.py` is another possible producer and assumes **millisecond** raw epochs, unlike the inspected raw 1m seconds. Thus exact processed-file source/exchange, open-vs-close meaning, timezone provenance and valid close-time derivation remain **UNKNOWN**. Do not infer them from the column name or use `timestamp+1h` in replay yet.

`data/history/raw/1m/provenance/{BTC,ETH}-USDT_1m_provenance.json` says `source: CSV` and records a loader-time checksum/range, not an originating exchange or candle-open/close contract; `CSVHistoryLoaderAdapter._record_data_provenance` creates that metadata *after reading* CSV. It does not prove processed 1h lineage. Separate `data/history/micro` files have OHLCV plus trade/taker fields; `scripts/fetch_microstructure.py` describes Binance futures klines and stores `k[0]//1000`, but no inspected per-file capture manifest proves these particular files were made by that invocation. They are 1m/5m/15m, **not** the frozen 1h processed cohort. No aggregation/substitution is authorized here.

## Bounded quality audit (read-only)

The scanner parsed every row in the 12 BTC/ETH candidate/nearby CSVs below, checked integer epoch parsing, finite positive OHLC, `low <= open,close <= high`, nonnegative volume, duplicates, order and exact expected spacing. It did not repair or drop rows. `longest` is contiguous rows at the file's named interval; `missing` is the minimum count implied by positive gaps. A malformed timestamp cannot be assigned an epoch span.

| Archive (both symbols unless shown) | Rows BTC / ETH | First-last epoch BTC; ETH | Duplicates / order / invalid | Gaps, missing, largest gap | Longest contiguous |
|---|---:|---|---|---|---:|
| `processed/1h` **frozen** | 721 / 722 | `1781874000–1784466000`; `1779397200–1781992800` | 0 / 0 / 0 each | 0 / 0 / 0 each | 721 / 722 |
| `raw/1h` | 72 / 72 | `1768330800–1768586400`; ETH **unparseable** | BTC 0; ETH 72 malformed timestamps | BTC 0; ETH not quantifiable | 72 / 0 |
| `raw/1m` | 2,563 / 2,568 | `1785661380–1785870420` both | 0 / 0 / 0 each | 15 gaps each; 922 / 917 missing; 12,840 / 11,820 seconds largest | 898 / 899 |
| `micro/1m` | 64,500 / 64,500 | `1780272000–1784141940` both | 0 / 0 / 0 each | 0 / 0 / 0 each | 64,500 each |
| `micro/5m` | 12,900 / 12,900 | `1780272000–1784141700` both | 0 / 0 / 0 each | 0 / 0 / 0 each | 12,900 each |
| `micro/15m` | 4,301 / 4,301 | `1780272000–1784142000` both | 0 / 0 / 0 each | 0 / 0 / 0 each | 4,301 each |

`raw/1h/ETH-USDT.csv` uses strings such as `1970-01-01 00:00:01.768334400` in the timestamp column, incompatible with the integer-epoch contract used by the processed 1h files. This is a distinct data-quality issue, not evidence for repairing the frozen cohort.

## Frozen cohort coverage gate

BTC processed 1h: 2026-06-19 13:00 to 2026-07-19 13:00 UTC, 721 adjacent rows (30 days plus one endpoint). ETH processed 1h: 2026-05-21 21:00 to 2026-06-20 22:00 UTC, 722 adjacent rows (30 days plus two endpoints). The apparent common timestamp range is 2026-06-19 13:00 through 2026-06-20 22:00 UTC: **34 rows per symbol, 33 elapsed hours**, with no gap *inside those file ranges*. The protocol further caps at 2026-07-19 00:00, which does not increase overlap. Thus total span and individually contiguous span are long, but **overlapping usable span is only 34 bars**. After the frozen 50-bar warmup there are zero eligible events in this common intersection. The frozen minimum is >=100 non-overlapping primary events **and >=20 distinct UTC days per symbol**; neither can be met. This fails coverage independently of unresolved timestamp provenance. No other symbol set is permitted by the preregistration.

Because provenance and coverage fail, no real-archive Watcher→Engine→Fusion prefix run was performed: `REAL_ARCHIVE_PREFIX_INVARIANCE_NOT_TESTABLE`. The earlier two-symbol fixture pass remains fixture-level only. No Edge study was run. No data are silently cleaned, relabeled or replaced.

## Separate full-Strategy blockers (not remediated)

`DecisionPipeline.process_execution_intent` gives absent `obi_ratio` direction-favoring ±0.15 (confirmation threshold ±0.1), absent `cvd` direction-favoring ±1.0 (sign threshold zero), and absent `best_bid`/`best_ask` prices at `current_price*(1∓0.0001)`. The first pair can make `ExecutionConfirmationEngine` pass; the latter can make `ExecutionOptimizer` pass its spread threshold and alter a maker limit price. These are **POTENTIAL_SYNTHETIC_SIGNAL_CONTAMINATION = PRESENT** in source, not a proven historical or Live occurrence rate or incident. `SetupEngine.scan_for_setups` calls `datetime.now()` after at least five prices to create `CandidateSetup.timestamp`; adapter freshness checks can consult that timestamp. This lies beyond the chosen pre-intent Fusion boundary and blocks later Strategy-level deterministic event-time research: `STRATEGY_LEVEL_EVENT_TIME = BLOCKED`. Existing XMR and broker-retry statuses unchanged.

## Safety and next action

The four protected production persistence SHA-256 values match the pre-audit checkpoint: active positions `11107b33…e1ab`, live orders `e72c03f3…f348`, cooldown `0607bcea…5c6a56`, trade journal `1eb076e6…da0d14`. No broker request, network collection, production order, outcome calculation or C-11/C-33/C-35/Compression mutation. Next action is **not** to swap datasets under this preregistration. Independently qualify and preregister a new, sufficiently overlapping candle cohort—with direct source/open-time proof—before any real-archive prefix or Edge outcomes; retain this cohort's data-insufficient result as recorded.
