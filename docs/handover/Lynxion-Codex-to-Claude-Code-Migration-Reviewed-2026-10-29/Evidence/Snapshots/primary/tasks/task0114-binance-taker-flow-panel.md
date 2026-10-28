# TASK-0114 — Official Binance Historical Taker-Flow Panel

**Status:** COMPLETE — DATA GATE KEEP

## Objective

Acquire and integrity-gate native Binance USD-M 15-minute total and taker-buy quote volume before
defining C21.

## Frozen Scope

- Official Data Vision `data/futures/um/daily/klines/` at native 15m.
- BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- 2023-01-01 through 2026-08-29, subject to archive availability.
- Verify every checksum; support headerless/headered and millisecond/microsecond source formats.
- Preserve open time, OHLC, quote volume, trade count, and taker-buy quote volume.
- Validate schema, timestamps, OHLC, finite/non-negative flow fields, taker-buy<=total quote volume,
  exact/conflicting duplicates, gaps, and primary/reverse coverage.
- No resampling, reconstruction, missing-data fill, outcome opening, or C21 specification.
- No production, broker, risk, trailing, symbol-admission, or order changes.

## Verified Result

- 8,022 official archives passed checksum verification.
- Every symbol contains exactly 128,352 unique native 15-minute rows.
- Schema, timestamp, OHLC, numeric, taker-flow, conflicting-duplicate, and gap violations are zero.
- Final verdict: **KEEP** with complete aligned coverage from 2023-01-01 through 2026-08-29.
- No C21 signal or outcome was opened during acquisition.
