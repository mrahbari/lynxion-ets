## Purpose

A compact, production-ready guide for integrating the Downloader / Sync Engine into the existing WFO project. 
This README focuses on what to add (only missing pieces), how to configure it, how to test it, and how to operate it — without changing existing public interfaces or rewriting current logic.

---

## Quick summary (what this delivers)

* Gap-free 1-minute OHLCV sync for many symbols
* Async network downloads + thread pool for local CPU work
* Atomic file writes and deterministic gap-filling
* Structured JSON logs and cycle reports
* On-demand watcher retune for priority repairs
* Minimal surface area changes: new modules only, existing interfaces preserved

---

## Project files to add / finalize

(Only implement missing modules; do not replace or rewrite existing files.)

```
file_manager.py         # read/write/validation/compaction (atomic writes + deterministic rules)
downloader_async.py     # async exchange API layer, retries/backoff, rate-limiter
sync_manager.py         # per-symbol orchestration, job queue, prioritization
sync_loop.py            # periodic scheduler and cycle orchestration
watcher_retune.py       # on-demand validation & priority repair

utils/
  logger.py             # structured JSON logger, error/backtrace handling

config/
  symbols.py            # authoritative symbol list and per-symbol metadata
  settings.py           # intervals, threadpool sizes, retry/backoff, rate limits
```

---

## Minimal .env (example)

```
SYNC_INTERVAL_SECONDS=7200
ASYNC_CONCURRENCY=100
DOWNLOAD_THREADPOOL_WORKERS=8
RETRY_MAX_ATTEMPTS=5
RETRY_BACKOFF_BASE=0.5
RETRY_BACKOFF_FACTOR=2.0
RATE_LIMIT_TOKENS_PER_SECOND=10
TEMP_FILE_SUFFIX=.partial
DATA_DIR=/data/history
```

---

## File manager responsibilities (atomic + deterministic)

1. Validate CSV schema and timestamps
2. Detect missing ranges per-file (return list of [start, end] intervals)
3. Provide merge primitives: merge_sorted_rows(existing, new)
4. Atomic save: write to `file.tmp{TEMP_FILE_SUFFIX}` → validate → move/replace
5. Compaction/retention: keep raw 1m files as-is, generate processed TFs (5m/15m/30m/1h) deterministic aggregation (open,high,low,close,sum(volume))
6. Row index/quick lookup: optionally maintain lightweight index file (`<symbol>.idx.json`) with earliest/latest timestamp + row count

Determinism: define fill rules (forward-fill or zero-fill) and document them clearly in SYNC-HISTORIES-README.md.

---

## Downloader (downloader_async.py)

* Exposes `async def fetch_range(symbol, start_ts, end_ts) -> AsyncIterator[CSVChunk]` or returns combined CSV rows.
* Use an async HTTP client (e.g. aiohttp/anyio-compatible) and a token-bucket rate limiter.
* Retry on transient errors (5xx, network errors, rate-limit) with exponential backoff + jitter.
* Respect per-exchange quotas (configurable per-symbol/exchange in `config/symbols.py`).
* Emit structured log events for each request: request_id, start_ts, end_ts, duration_ms, status_code, attempts.

---

## Sync Manager (sync_manager.py)

* Main orchestration unit per-symbol. Responsibilities:

  * Determine missing ranges from file_manager
  * Split ranges into exchange-allowed pages (API window limits)
  * Schedule async downloads with concurrency limited by ASYNC_CONCURRENCY and rate-limiter
  * On download completion: hand off raw rows to thread pool for parsing/merge/validate via file_manager
  * Keep a per-symbol lock to prevent concurrent conflicting writes
  * Emit per-symbol JSON log entries (ranges fixed, rows, bytes, duration)
  * If download fails after retries, mark cycle-level error but continue other symbols

Design notes:

* Use an in-memory priority queue for on-demand watcher requests.
* Keep minimal in-process state; persistent state only in files and small index files.

---

## Sync Loop (sync_loop.py)

* Global cycle runner. Responsibilities:

  * Run continuous cycles every SYNC_INTERVAL_SECONDS
  * For each cycle: gather symbol list from config/symbols.py and enqueue per-symbol jobs in sync_manager
  * Limit overall concurrency (global semaphore)
  * Produce cycle report JSON at cycle end: summary (symbols scanned, symbols fixed, rows written, bytes, total duration, errors)
  * Save cycle report to `reports/cycle-<iso>.json`

---

## Watcher Retune (watcher_retune.py)

* API for strategies/watchers to request priority repair of a symbol and interval.
* Validate requested interval; perform quick local validation; if gaps detected, enqueue priority job.
* Only return `data ready` when the file_manager confirms the requested interval is gap-free.
* Should be callable synchronously by strategy code (wrap the internal async repair and wait) or async depending on host.

---

## Logging format (structured JSON)

Every top-level operation should write a single JSON line to logs with at least the following keys:

```
{
  "timestamp": "2025-12-11T12:34:56Z",
  "operation": "cycle|symbol_download|watcher_repair",
  "symbol": "BTC-USD",
  "status": "ok|partial|error",
  "fixed_ranges": [[start_ts, end_ts],...],
  "api_usage": {"requests": 5, "rate_limit_events": 0},
  "duration_ms": 1234,
  "rows_written": 1440,
  "bytes_written": 102400,
  "error": {"message":"...","backtrace":"..."}
}
```

---

## Tests & Validation (end-to-end checklist)

1. Unit tests for file_manager: detect gaps, atomic write, merge semantics.
2. Unit tests for downloader: retry logic, rate-limiter behaviour (mock HTTP client).
3. Integration test (local): create small fake exchange server that responds with CSV slices -> run sync_manager for 2 symbols and assert continuous 1m file after run.
4. Watcher test: request a priority repair for a small missing interval and assert the function blocks until ready.
5. Backtest readiness: verify processed TF generation and deterministic aggregation.
6. CI: ensure new tests run without modifying existing tests.

---

## Run / Debug commands

* Run single cycle for a single symbol (dry run):

```
python -m sync_loop --one-cycle --symbol BTC-USD --dry-run
```

* Run watcher repair (blocking):

```
python -m watcher_retune --symbol BTC-USD --from 1672531200 --to 1672617600
```

* Start continuous loop (foreground):

```
python -m sync_loop
```

---

## Compatibility & Safety rules (must follow)

* Do not change public function signatures used elsewhere. If you must add helpers, keep them private.
* When writing files, always write to a temp file then rename (atomic on POSIX).
* Any configuration defaults must be in config/settings.py and read by environment in a single place.
* No side-effects on startup. E.g., starting the module must not alter files unless a sync cycle runs.

---

# SYNC-HISTORIES-README.md

## Purpose

Define the data retention, compaction, and deterministic gap-filling rules. Keep this document short and prescriptive so backtests are deterministic.

---

## Data layout (on disk)

```
/data/history/raw/1m/<SYMBOL>.csv         # authoritative 1m raw (may have gaps before sync)
/data/history/processed/5m/<SYMBOL>.csv
/data/history/processed/15m/<SYMBOL>.csv
/data/history/processed/30m/<SYMBOL>.csv
/data/history/processed/1h/<SYMBOL>.csv
/data/history/index/<SYMBOL>.idx.json     # optional: earliest/latest ts, rows
/reports/cycle-<ISO>.json                 # per-cycle report
/logs/sync.log                            # JSONL
```

---

## Compaction & retention policy

* Raw 1m files: keep last 365 days (configurable)
* Processed TFs: keep last 3 years
* Older raw data can be archived to cold storage via an external job (not implemented here)

Retention enforcement: run as part of file_manager.compact() once per cycle.

---

## Deterministic gap-filling rules

1. Missing single-minute rows within an otherwise contiguous section: forward-fill `close`, set `open==close`, `high==low==close`, `volume==0`.
2. Missing start-of-file ranges (no prior data): use first available remote bar as-is; do NOT invent earlier bars.
3. Large gaps: if gap longer than `MAX_GAP_FILL_MINUTES` (configurable, default 1440), mark as `partial` and do NOT auto-fill — leave an explicit marker row with `__GAP__` metadata and let watcher_retune be used to fill when requested.
4. Compaction must be deterministic; document the aggregation function (OHLCV: open from first, high=max, low=min, close from last, volume=sum).

---

## File format & validation

* CSV columns: `timestamp,open,high,low,close,volume`
* Timestamp = unix seconds (UTC) at minute resolution (seconds=0)
* Validation fails if timestamps not increasing or duplicate timestamps exist after merge.
* When validation fails, keep a backup of the previous file as `<symbol>.bak.<iso>` and log an error. Do not overwrite the previous file until the new file validates.

---

## Example JSON cycle report (short)

```
{
  "cycle_start": "2025-12-11T08:00:00Z",
  "cycle_end": "2025-12-11T08:04:32Z",
  "symbols_scanned": 1200,
  "symbols_fixed": 1180,
  "rows_written": 1_440_000,
  "bytes_written": 512_000_000,
  "errors": [
    {"symbol":"FOO-BAR","error":"rate_limit_exhausted","attempts":5}
  ]
}
```

---

## Developer checklist before merging

* [ ] README reviewed and placed at project root
* [ ] `config/settings.py` updated with default values
* [ ] Implement missing modules only (avoid rewriting existing code)
* [ ] Unit tests added and passing
* [ ] Integration test (local fake exchange) added and passing
* [ ] Logging format verified (JSONL) and aggregated by existing log pipeline
* [ ] Add README run commands and CI steps

---

## Troubleshooting

* If many rate-limit events appear: reduce ASYNC_CONCURRENCY and increase rate-limiter tokens-per-second or add per-exchange throttles.
* If atomic replace fails on Windows: ensure using cross-platform atomic rename library or fallback safe-write pattern.
* If backtests see inconsistent data: re-run sync for affected symbols and check `reports/cycle-<iso>.json` for partial errors.

---

## Final notes

* Keep all new modules focused and small. Aim for testable units with minimal side-effects.
* Document any additional behavior in code docstrings and update these README files.
