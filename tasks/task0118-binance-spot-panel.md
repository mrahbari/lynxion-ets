# TASK-0118 — Official Binance Historical Spot Panel

**Status:** COMPLETE — KEEP

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

## Verified Result

- Downloaded and checksum-verified 8,022 official daily archives (1,337 per symbol).
- Retained 128,346 complete native 15-minute rows per symbol from 2023-01-01 through
  2026-08-29, with zero schema, numeric, timestamp, OHLC, duplicate, or flow violations.
- Censused and excluded one zero-volume partial source candle per symbol during the common
  2023-03-24 Binance maintenance interval. The resulting six missing intervals per symbol
  remain explicit; no fill or synthetic observation was introduced.
- Every retained spot timestamp aligns to the official futures panel: 128,346 common rows per
  symbol, zero spot-only rows, and six futures-only maintenance-interval rows.
- Data gate: **KEEP**. This result authorizes preregistration only; it does not establish a
  profitable edge or authorize production trading.

## Test Evidence

- Focused acquisition/parser suite: 5 passed.
