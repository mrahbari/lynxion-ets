# TASK-0163 — Forced-Liquidation Event Collector

**Status:** COMPLETE AT REPOSITORY LEVEL — NETWORK NOT ACTIVATED

## Objective

Implement only C-33's append-only public liquidation, closed-kline, heartbeat, and session-lifecycle
collection layer without calculating a signal or outcome.

## Result

- `scripts/collect_c33_liquidation_events.py` parses only frozen USD-M, symbol-consistent, filled
  liquidation snapshots and exact closed one-minute candles, preserving raw bytes, hashes,
  event/receipt time, session identity, and the explicit censored-snapshot label.
- Public server-time heartbeat and STARTED/ENDED lifecycle records make later five-minute liveness
  classification possible. Append-only persistence deduplicates restarts and fails on corrupt state.
- The CLI is fail-closed unless `--enable-network` is explicit. It was not activated, and no signal,
  threshold, return, verdict, broker, order, or runtime path was opened.
- Eight focused tests and the full suite pass with 911 passed and one optional import-linter skip.

## Next Unit

TASK-0164 must independently review stream URL/schema, reconnect and interruption semantics,
boundary enforcement, and failure injection. Only after a passing review may it freeze a separate
forward activation manifest; the review itself must not connect to the stream.
