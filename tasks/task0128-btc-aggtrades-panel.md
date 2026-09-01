# TASK-0128 — Bounded Official BTC Aggregate-Trades Panel

**Status:** IN PROGRESS — ACQUISITION PROTOCOL FROZEN

## Objective

Build a reproducible BTCUSDT 15-minute aggregate-trade feature panel from a storage-feasible bounded
official corpus, without defining or opening a trading candidate.

## Frozen Scope

- Official Futures UM daily `aggTrades` ZIP/checksum pairs, BTCUSDT only.
- 2024-01-01 through 2026-08-29 inclusive; no earlier/later dates.
- Retain checksum-verified compressed raw archives; process one archive at a time.
- Never materialize the fully expanded corpus.
- Normalize native 15-minute UTC buckets with trade count, total quote volume, buyer-initiated and
  seller-initiated quote volume, signed imbalance, maximum quote size, mean/std quote size, and
  top-1% quote-volume share using a per-bucket exact quantile.
- Preserve maker semantics: `is_buyer_maker=true` is seller-initiated.
- Validate schema, finite positive price/quantity, millisecond/microsecond timestamps, monotonic
  IDs/times, duplicates/conflicts, bucket alignment, coverage/gaps, checksums, and deterministic hash.
- Maintain at least 20 GiB free space throughout; fail closed before a download that breaches it.
- No signal, threshold, candidate, PnL, order, or production/risk/trailing change.

## Data Gate

- Every expected daily ZIP/checksum pair present and verified.
- Zero core schema/numeric/timestamp/side/duplicate/conflict violations.
- At least 90,000 normalized 15-minute buckets with explicit, unfilled gaps.
- Storage reserve preserved.
- Passing verdict is `KEEP` for later preregistration only.
