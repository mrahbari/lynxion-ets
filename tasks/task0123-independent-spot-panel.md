# TASK-0123 — Independent Official Binance Spot Panel

**Status:** COMPLETE — KEEP

## Objective

Acquire the official native 15-minute spot prices required for a disjoint, unchanged historical
confirmation of C-24 without opening basis-conditioned outcomes.

## Frozen Scope

- Official Data Vision `data/spot/daily/klines/` archives.
- DOGEUSDT, LINKUSDT, LTCUSDT, DOTUSDT, AVAXUSDT only.
- 2023-01-01 through 2026-08-29, subject to official availability.
- Reuse TASK-0118 checksum, schema, timestamp, OHLC, duplicate, partial-source-candle, gap, and
  normalization rules unchanged.
- Align timestamps to the already acquired C-22 native futures panel; report common, spot-only,
  and futures-only rows per symbol without fill or interpolation.
- KEEP requires zero core integrity violations and at least 120,000 complete rows per symbol.
- Acquisition may not compute basis, signal counts, trades, PnL, or candidate verdicts.
- No orders or production/risk/trailing/symbol-admission changes.

## Verified Result

- Downloaded and checksum-verified 6,685 official archives (1,337 per symbol).
- Retained 128,346 complete native 15-minute rows per symbol with zero schema, numeric,
  timestamp, OHLC, duplicate, or flow violations.
- Excluded and censused one zero-volume partial maintenance candle per symbol. Six missing
  intervals per symbol remain explicit; no observation was filled or synthesized.
- Every retained spot timestamp aligns to the C-22 futures panel: 128,346 common rows,
  zero spot-only rows, and six futures-only maintenance rows per symbol.
- Frozen data verdict: **KEEP**. No basis or trading outcome was computed.
