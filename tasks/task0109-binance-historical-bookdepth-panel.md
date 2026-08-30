# TASK-0109 — Official Binance Historical Book-Depth Panel

**Status:** COMPLETE — DATA GATE KEEP

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

## Verified Result

- 8,002 official archives passed Binance SHA-256 verification.
- The six-symbol panel contains 380,974–381,838 normalized five-minute rows per symbol.
- Conflicting duplicates, schema violations, invalid expected levels, numeric violations, and
  incomplete snapshots are all zero.
- Binance's later official `-5.00` representation is accepted as the same frozen integer level.
- Official `-0.20` and `+0.20` rows are measured separately as extra levels and excluded from the
  frozen ten-level panel; no expected level is synthesized.
- Final gate: `KEEP` with adequate coverage and zero integrity violations.
- No price outcome was opened and no C18 hypothesis was evaluated during acquisition.
