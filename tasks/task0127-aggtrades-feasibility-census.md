# TASK-0127 — Official Aggregate-Trades Feasibility Census

**Status:** IN PROGRESS — LISTING-ONLY PROTOCOL FROZEN

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
