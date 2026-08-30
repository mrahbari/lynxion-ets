# TASK-0112 — Official Binance Historical Premium-Index Panel

**Status:** IN PROGRESS — ACQUISITION PROTOCOL FROZEN

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
