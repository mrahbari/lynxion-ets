# Timeframe Refactor Report

**Date:** 2026-06-12. Documents the timeframe re-architecture that moves the production
strategies off 1m as their decision timeframe, per the post-Phase-6 mandate. No strategy
code, parameters, or hypotheses were changed — only the *timeframe of the data* each
strategy decides on.

## Motivation
Rehabilitation established that **1m is structurally cost-incompatible**: the ATR-scaled
take-profit (2.25×ATR ≈ 0.10% on 1m BTC) is ~3× smaller than the 0.30% round-trip cost
(fee 0.10%×2 + slippage 0.05%×2). Cost-breakeven ≈ 15m. Deciding on 1m guarantees
sub-cost trades. The refactor evaluates strategies on cost-viable timeframes.

## Architecture
- **Canonical data feed remains 1m.** The broker/source data is unchanged — 1m candles
  are the single source of truth. We did **not** switch the data source.
- **Higher timeframes are produced by resampling 1m → 5m / 15m / 30m / 1h.**
- **Timeframe roles (intended MTF design):**
  - 1h — macro trend filter
  - 30m — trend confirmation
  - 15m — primary signal timeframe
  - 5m — entry refinement
  - 1m — execution only (never the primary decision TF)

## Resampling & MTF hygiene (downsample → ffill → shift → align, no lookahead)
- **Downsample:** OHLCV aggregation per interval — open=first, high=max, low=min,
  close=last, volume=sum (pandas `resample`).
- **No lookahead:** a higher-TF bar is only consumed once *closed*; the backtester feeds
  completed bars sequentially, and all derived indicators (e.g. `df['atr']` = TR.rolling(14)
  **.shift(1)**) are shifted one bar — so no bar uses its own or future data.
- **ffill / shift / align:** when a coarser-TF series is overlaid on a finer one, it is
  forward-filled and shifted so each finer bar sees only the last *closed* coarser bar
  (alignment without leakage). For this validation each strategy decides on a single
  resampled TF (15m/30m/1h), so alignment reduces to "use closed bars only."
- **Epoch correctness:** resampled `timestamp` written as
  `(index − 1970-01-01) // 1s` (an earlier `astype('int64')` attempt corrupted timestamps
  to 1970 and was fixed).

**Resampled coverage (from 1m, ~1 year, per symbol BTC/ETH/SOL):**

| TF | bars (BTC) | role |
|----|----|----|
| 5m | 105 122 | entry refinement |
| 15m | 35 042 | primary signal |
| 30m | 17 521 | trend confirmation |
| 1h | 8 761 | macro filter |

Files: `data/history/raw/<tf>/<SYMBOL>.csv` (untracked data).

## Implementation (reused evaluation framework — no new research)
- **`BACKTEST_TIMEFRAME` env hook** (default-preserving): when set, the data layer reads
  `data/history/raw/<tf>/` instead of `1m`. Touch points:
  - `infrastructure/data_sync/file_repository_adapter.py` — `get_raw_file_path` swaps the
    timeframe leaf dir.
  - `application/use_cases/run_backtest.py` — passes the timeframe through the loader.
  Unset → canonical 1m behavior, byte-for-byte unchanged.
- **`research/profitability_diagnostics/higher_tf_eval.py`** — runs the production
  backtest matrix at a given TF (`BTC/ETH/SOL × 90/180/365d × 12 strategies`), writes
  `eval_matrix_<tf>.json`, resumable, never collides with the canonical `eval_matrix.json`.

## Validation performed
All 12 production strategies re-evaluated on **BTC/ETH/SOL × {15m, 30m, 1h}** with
existing parameters (no tuning). Results in `timeframe-validation-report.md`,
`cross-symbol-stability-report.md`, `production-candidate-ranking.md`, and
`final-deployment-readiness-report.md`.

## Key architectural finding
The refactor works as intended (strategies now decide on cost-viable bars), and it
surfaced a calibration nuance: **15m sits on the cost-breakeven cliff** (TP ≈ 0.57% vs
0.30% cost — thin margin) and is empirically *worse* than 1h. **1h is the most
cost-robust horizon** of those tested. The mandate's "15m = primary signal TF" is
therefore the least cost-robust viable choice; 1h is recommended for any future viability
work. (This is an observation, not a parameter change.)
