# TASK-0109 — Official Binance Historical Book-Depth Panel

**Status:** IN PROGRESS — ACQUISITION PROTOCOL FROZEN

## Objective

Acquire and validate official Binance USD-M aggregated book-depth history before defining any
L2 candidate.

## Frozen Scope

- Source: `data/futures/um/daily/bookDepth/` on official Binance Data Vision.
- Universe: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Range: 2023-01-01 through 2026-08-29, subject to archive availability.
- Expected schema: timestamp, percentage, depth, notional.
- Expected levels per complete snapshot: -5,-4,-3,-2,-1,+1,+2,+3,+4,+5.
- Raw archives remain local; tracked manifest records every source key/hash and summarized
  normalized-file hashes and integrity census.

## Acceptance Criteria

- Official SHA-256 verification and resume are tested.
- Schema, timestamp, level, finite/non-negative values, exact/conflicting duplicates, incomplete
  snapshots, and cadence gaps are measured.
- No missing snapshot or level is synthesized.
- No price outcome or C18 result is evaluated during acquisition.
- Data verdict is KEEP or REJECT before candidate preregistration.
- No production, broker, order, or risk interaction.
