# TASK-0128 — Bounded Official BTC Aggregate-Trades Panel

**Status:** COMPLETE — DATA GATE KEEP

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

## Final Evidence

- All 972 expected daily ZIP/checksum pairs from 2024-01-01 through 2026-08-29 were acquired and
  verified.
- The normalized panel contains 93,312 complete native 15-minute rows with zero missing intervals,
  exact duplicates, or conflicting duplicates.
- Core schema, numeric, timestamp, side, duplicate-ID, and ID/time violations are all zero.
- The normalized artifact SHA-256 is
  `3e5975b6e1369685877c57944375a330548515ce7eb064f240b3c81885ef9edf`.
- The 20 GiB storage reserve remained preserved. Final verdict: `KEEP` for preregistration only.
