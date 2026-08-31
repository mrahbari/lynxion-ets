# TASK-0118 — Official Binance Historical Spot Panel

**Status:** IN PROGRESS — ACQUISITION PROTOCOL FROZEN

## Objective

Acquire and validate official native 15-minute spot prices required for a future delta-neutral
spot/perpetual carry test.

## Frozen Scope

- Official Data Vision `data/spot/daily/klines/` at native 15m.
- BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- 2023-01-01 through 2026-08-29, subject to archive availability.
- Official checksum verification and resumable local raw cache.
- Validate headerless/headered and millisecond/microsecond formats, timestamps, OHLC, finite
  non-negative volume, exact/conflicting duplicates, gaps, and aligned coverage.
- No fill, resampling, C23 signal, carry threshold, holding rule, or outcome opening.
- No production, broker, risk, trailing, symbol-admission, or order changes.
