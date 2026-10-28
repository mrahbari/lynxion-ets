# TASK-0159 — Cross-Venue Public-Book Collector

**Status:** COMPLETE AT REPOSITORY LEVEL — FORWARD COLLECTION NOT ACTIVATED

## Objective

Implement the minimal standalone C-32 public depth collector under the frozen TASK-0158 contract,
without opening outcomes or touching broker/runtime paths.

## Result

- `scripts/collect_c32_cross_venue.py` independently fetches public Binance/BingX perpetual depth,
  preserves raw payload hashes, validates server time/skew/staleness and sorted uncrossed books,
  walks depth for one identical base quantity, calculates both executable spread directions, and
  appends prospective observations with boundary and duplicate guards.
- Network access is fail-closed unless `--enable-network` is explicit. No network call was made in
  this task.
- Disconnected tests cover both response shapes, VWAP depth walking, identical quantity/direction,
  skew, staleness, future timestamps, malformed/crossed books, strict boundary, restart duplicate,
  and corrupt-ledger behavior.
- Ten focused tests and the full suite pass with 902 passed and one optional import-linter skip.

## Next Unit

TASK-0160 must independently review endpoint response semantics and collector failure injection,
then freeze an activation manifest before the first public-data call. It may not change C-32's
signal or gate and may not invoke a broker, order, runtime, or authenticated endpoint.
