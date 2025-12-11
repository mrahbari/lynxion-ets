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