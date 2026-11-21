# TASK-0127 — Official Aggregate-Trades Feasibility Census

**Status:** COMPLETE — NO_GO

## Objective

Determine whether an official BTC/ETH aggregate-trade panel is feasible before any bulk download or
new candidate definition.

## Acceptance Criteria

- List official daily `data/futures/um/daily/aggTrades/` objects for BTCUSDT and ETHUSDT from
  2023-01-01 through 2026-08-29.
- Validate one ZIP and one checksum key per expected date; report missing/duplicate dates.
- Sum compressed archive bytes and estimate temporary/normalized storage separately.
- Compare the estimate to current free workspace storage using a conservative safety reserve.
- Optionally download at most one archive per symbol solely for schema/integrity sampling.
- Emit a deterministic feasibility report with `GO` or `NO_GO`; do not download the corpus,
  aggregate features, define signals, or open outcomes.
- No production or order-path changes.

## Verified Result

- Complete official coverage exists for both BTCUSDT and ETHUSDT: 1,337 ZIP/checksum pairs per
  symbol from 2023-01-01 through 2026-08-29, with no missing dates.
- Two downloaded schema samples passed SHA-256 and contained the expected seven aggregate-trade
  fields.
- The compressed corpus is 49,175,610,837 bytes (~45.8 GiB); conservative full expansion is
  ~277 GiB. A resumable raw-cache/streaming workflow plus the frozen 20 GiB reserve requires more
  than the currently available ~57.9 GiB.
- Frozen feasibility verdict: **NO_GO**. No bulk corpus was downloaded and no signal/outcome was
  constructed.

Machine report: `docs/reports/aggtrades_feasibility.json`.
