# TASK-0228 — Investor-release cost-adjusted baseline

## Scope

Freeze a reproducible descriptive baseline from the canonical local trade journal. Do not tune,
change trading behavior, or reinterpret historical subsets as prospective evidence.

## Evidence

- Input: 1,913 rows, 1,257 final trade IDs after 656 duplicate rows are resolved by final record.
- Recorded PnL: -14,935.7042 USDT; recorded signed fees: -559.710655 USDT.
- Cost-adjusted PnL: -15,495.414855 USDT; expectancy: -12.32729901 USDT/trade;
  PF: 0.15008542; max drawdown: 15,557.062582 USDT.
- The journal mixes materially different sizing/risk eras: average notional is 985.21 USDT and
  56 trades exceed 1,000 USDT, whereas the current VST per-order cap is 21 USDT.
- Regime is missing for all 1,257 records; confidence and initial SL/TP are missing for 747;
  MFE, MAE, slippage, and funding are unavailable in this artifact.
- The post-hoc `<=25 USDT` bucket is positive (N=719, +0.26955 USDT expectancy, PF 2.442), but
  it is descriptive only: it was not preregistered, is not OOS, and has no uncertainty or
  temporal-stability gate. It cannot admit a strategy.
- MeanReversion (N=106) and OIFootprint (N=14) are positive descriptive slices, but neither is
  eligible evidence for the same reasons; OIFootprint is especially under-sampled.

## Reproducibility

The manifest freezes the input/output SHA-256 hashes and exact generation command. The generated
artifact contains overall and strategy, symbol, side, timeframe, regime, confidence, duration,
exit, and position-size breakdowns.

## Verdict

`NO_TRADE_DEFAULT`. Aggregate economics are decisively negative and no positive slice clears a
prospective/OOS evidence floor. This does not erase the limited positive descriptive leads; they
must be preregistered against a fresh boundary before any strategy admission.
