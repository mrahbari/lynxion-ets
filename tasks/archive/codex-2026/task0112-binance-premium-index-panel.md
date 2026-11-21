# TASK-0112 — Official Binance Historical Premium-Index Panel

**Status:** COMPLETE — DATA GATE KEEP

## Objective

Acquire and validate official Binance USD-M 15-minute premium-index history before defining C20.

## Frozen Scope

- Source: official Data Vision `data/futures/um/daily/premiumIndexKlines/`.
- Universe: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Range: 2020-01-01 through 2026-08-29, subject to per-symbol archive availability.
- Interval: native 15m; no resampling or fill.
- Verify every official checksum and record archive/source hashes in a tracked manifest.
- Validate schema, symbol/range binding, exact/conflicting duplicates, timestamp alignment and
  monotonicity, OHLC consistency, finite values, and missing intervals.
- Volume/count fields are structural archive fields and are not admitted as market-flow features.

## Acceptance Criteria

- Acquisition and resume/checksum behavior have regression tests.
- Core integrity violations are zero and coverage is adequate for both temporal samples.
- Missing archives/intervals remain explicit; no data is synthesized.
- No price outcome or C20 signal is opened before the data verdict.
- No production, broker, risk, trailing, symbol-admission, or order behavior changes.

## Verified Result

- 14,101 official archives passed Binance SHA-256 verification.
- The panel contains 205,981–233,560 unique native 15-minute rows per symbol.
- Every symbol has exactly 35,040 reverse-sample rows and 93,216–93,312 primary-sample rows.
- Schema, numeric, timestamp, OHLC, and conflicting-duplicate violations are all zero.
- 15,885 source-gap intervals are explicitly retained, concentrated in a few historical archive
  outages; no gap is filled or synthesized.
- Final gate: `KEEP` with adequate sample coverage and zero core integrity violations.
- No C20 signal or price outcome was opened during acquisition.
