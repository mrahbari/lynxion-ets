# Edge Candidate Register v25 — C-26 BTC-Lead / Alt-Underreaction

**Status:** OPENED — C-26 REJECTED

C-26 tests delayed cross-market propagation after a causally extreme completed BTC hourly move.
It is a market-context lead/lag mechanism, distinct from own-symbol momentum, simultaneous
cross-sectional ranking, and taker-flow continuation.

## Frozen Data and Boundaries

- Official TASK-0094 native 15-minute USDT perpetual OHLC for BTCUSDT and the traded universe
  ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Official funding histories already isolated under `data/research/c16/funding/`.
- Exact common timestamps only; no fill, interpolation, nearest match, or resampling.
- Primary: 2024-01-01 through 2026-08-29. Reverse: 2023-01-01 through 2023-12-31.
- Four global chronological primary folds formed from eligible entry timestamps.

## Frozen Signal

- Construct non-overlapping UTC-aligned completed hourly bars from exactly four contiguous native
  15-minute bars. Hourly return is first open to fourth close; incomplete hours are rejected.
- For BTC, compute causal absolute-return p95 from the previous 720 completed hourly observations,
  excluding current.
- A BTC shock requires absolute hourly return strictly above both its causal p95 and 1.50%.
- For each alt at the same completed hour, define signed response ratio as
  `alt_hourly_return / BTC_hourly_return`.
- The alt underreaction signal requires `0 <= signed response ratio <= 0.35`. Thus the alt has
  started moving in the BTC direction but completed no more than 35% of BTC's proportional move.
- BTC direction determines LONG for a positive shock and SHORT for a negative shock. No other
  regime, volume, symbol, or diagnostic filter is applied.

## Frozen Execution and Economics

- Enter the eligible alt at the first exact common 15-minute open after the completed signal hour.
- Exit at the exact open 16 native bars after entry (four hours). Reject missing/non-contiguous
  paths and per-symbol overlapping positions.
- Include official alt funding settlements strictly after entry and at or before exit: LONG pays
  `funding_rate`, SHORT receives it.
- Use prior-bar information only; entry/exit opens provide execution prices and cannot affect the
  signal. Charge 0.30% round trip; sensitivities are 0.20% and 0.50%.

## Frozen Reporting and Gate

- Report complete-hour/signal/underreaction/path/overlap census, sides, folds, five symbols, annual
  cells, BTC shock magnitude, response ratio, funding, cost sensitivity, holding return, and
  positive-PnL symbol concentration.
- Cluster bootstrap 10,000 samples by BTC signal timestamp with seed 260026 so simultaneous alt
  entries are one event cluster.
- KEEP requires every condition: primary N>=400; expectancy>0; PF>1; clustered 95% lower bound>0;
  >=3/4 positive folds with N>=60; both LONG and SHORT positive with N>=100; >=4/5 positive symbols
  with N>=50; positive-PnL concentration<=35%; reverse N>=100 with expectancy>0 and PF>1; and
  positive primary expectancy at 0.50% cost.
- Any failed condition is REJECT. A pass is only KEEP_FOR_PROSPECTIVE_VALIDATION.

## Frozen Prohibitions

No shock floor, percentile/lookback, response band, direction, horizon, cost, funding rule, universe,
fold, or gate may change after outcome opening. No production, broker, risk, trailing,
symbol-admission, paper-order, or real-order action is authorized.

## Frozen Result

C-26 produced 103 primary trades with -0.2102% expectancy, PF 0.744, and a clustered interval that
crossed zero. Only one fold was positive; LONG was negative, only ETH/SOL were positive with small
samples, and N missed the frozen minimum. Reverse 2023 was decisively negative (-0.9667%, PF 0.238,
N=49) with every fold, side, and symbol negative. Verdict **REJECT**. Machine report:
`docs/reports/edge_candidate_c26.json`.
