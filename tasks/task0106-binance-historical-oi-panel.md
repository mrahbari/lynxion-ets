# TASK-0106 — Official Binance Historical OI Metrics Panel

**Status:** COMPLETE — DATA GATE KEEP

## Objective

Acquire and validate the newly discovered official Binance Data Vision USD-M Futures metrics
archive before defining any OI-based edge candidate.

## Frozen Scope

- Source: `data/futures/um/daily/metrics/` on official Binance Data Vision.
- Universe: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Range: 2020-09-01 through 2026-08-29, subject to actual listing/archive availability.
- Raw archives remain outside Git; a tracked manifest records source keys, official checksums,
  downloaded hashes, rows, unique timestamps, coverage, gaps, and schema violations.
- Exact timestamp duplicates are deduplicated deterministically; conflicting duplicates fail.

## Acceptance Criteria

- Acquisition is deterministic and retry-safe.
- Official `.CHECKSUM` values are verified where supplied.
- Schema, symbol, timestamp, numeric, duplicate-conflict, and gap checks are tested.
- No price outcome or C-16 conditional result is evaluated during acquisition.
- Data gate returns KEEP or REJECT before candidate preregistration.
- No broker, order, production, or risk-control interaction.

## Result

- 10,854 official daily archives downloaded and verified against Binance SHA-256 files.
- 3,199,837 raw rows normalized to 3,124,582 unique five-minute timestamps.
- 75,255 exact BTC duplicates were deterministically removed; conflicting duplicates: zero.
- Schema, symbol, core-OI numeric, and checksum violations: zero.
- 1,372 missing five-minute intervals are explicitly recorded and were not synthesized or
  forward-filled.
- Auxiliary ratio missingness is separately censused and does not invalidate complete core OI
  quantity/value fields.
- All six symbols exceed 100,000 unique observations. Frozen data verdict: **KEEP**.

The 249MB raw/normalized store remains local and ignored; the source-key/checksum manifest is
tracked. No price outcome or C-16 conditional result was evaluated.
