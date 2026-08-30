# TASK-0094 — Aligned Futures Research Panel

**Status:** IN PROGRESS — DATASET SPECIFICATION FROZEN

## Problem Evidence

C-05 loaded 470 symbol files, but 915/920 four-hour decisions failed the frozen minimum
30-symbol alignment rule. Inspection also shows that the existing long-history helper calls
Binance Spot `/api/v3/klines`, while the research target and production market are perpetual
futures. Reusing or extending those nominal `raw` files would silently mix market semantics.

## Objective

Build a reproducible, isolated Binance USDT-margined perpetual 15m panel without overwriting
the production/raw stores, then verify alignment and integrity before any candidate result.

## Frozen Dataset Specification

- Source endpoint: public Binance Futures `https://fapi.binance.com/fapi/v1/klines`.
- Symbols: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`.
  This is the project's pre-existing comprehensive-validation default, selected before this
  task and not from observed C-05 performance.
- Interval: native 15m futures bars.
- Requested UTC range: 2023-01-01 00:00 through 2026-08-29 23:45 inclusive.
- Storage: `data/research/c06/binance_futures_15m/`; existing history files are untouched.
- Each row records open timestamp in epoch seconds and OHLCV. Only closed bars at or before the
  frozen end are accepted.
- A manifest records endpoint, request bounds, per-symbol first/last timestamp, row count,
  missing/duplicate/nonpositive/OHLC violations, and SHA-256.
- The aligned panel is the exact timestamp intersection across all six symbols; no price or
  volume forward-fill is permitted.

## Acceptance Criteria

- Pagination is deterministic, rate-limited, retrying, and rejects malformed API responses.
- Unit tests cover pagination progress, deduplication, closed-range filtering, and integrity.
- All six files pass timestamp, duplicate, OHLC, and positivity checks.
- The exact aligned interval and sample count are documented before C-06 is preregistered.
- No production strategy, broker, risk control, or existing data file changes.

## Decision Gate

KEEP the dataset only if all six symbols have at least 30,000 aligned 15m bars and zero
integrity violations. Otherwise document the blocker and do not weaken the gate post-result.
