# Edge Candidate Register v23 — C-24 Delta-Neutral Basis Convergence

**Status:** PREREGISTERED — OUTCOME UNOPENED

C-24 tests whether an unusually large positive perpetual premium over spot converges after an
equal-notional LONG-spot/SHORT-perpetual entry. This direct basis-dislocation mechanism is distinct
from directional premium-index C-20 and funding-selected carry C-23.

## Frozen Data and Boundaries

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- TASK-0118 official spot and TASK-0094 official perpetual native 15-minute OHLC panels.
- Official funding histories already isolated under `data/research/c16/funding/`.
- Exact common timestamps only; no fill, interpolation, nearest match, or resampling.
- Primary: 2024-01-01 through 2026-08-29. Reverse: 2023-01-01 through 2023-12-31.
- Four global chronological primary folds formed from eligible entry timestamps.

## Frozen Signal

- For each completed common 15-minute bar, define close basis as
  `perpetual_close / spot_close - 1`.
- Compute the causal p99 from the preceding 2,880 completed common basis observations for that
  symbol, excluding the current bar.
- Signal only when current basis is strictly positive and greater than both its causal p99 and
  0.40%. The absolute floor requires an observed dislocation capable of exceeding primary costs.
- Negative basis is excluded because executable spot borrowing availability and borrow cost are
  not present in the historical panel. No synthetic short-spot leg is allowed.

## Frozen Execution and Economics

- Enter equal-notional LONG spot and SHORT perpetual at the first exact common 15-minute open
  after the signal bar. Reject the event if either exact open is missing.
- Starting with the entry bar, evaluate basis only after each bar completes. Exit both legs at
  the next exact common open after the first completed bar whose basis is <=0.05%; otherwise exit
  at the exact common open 96 bars after entry (24-hour timeout).
- Reject overlapping positions per symbol. Exit-trigger bars contribute no close-price PnL;
  execution uses only the following opens.
- Include every official perpetual funding settlement strictly after entry and at or before exit.
  The SHORT receives positive funding and pays negative funding.
- One notional unit per leg, no leverage benefit. Capital-normalized gross return is
  `(spot long return + perpetual short return + short funding cashflow) / 2`.
- Primary round-trip cost is 0.20% of gross capital; sensitivities are 0.15%, 0.30%, and 0.50%.
  No collateral yield, maker rebate, borrow income, or optimistic execution credit is included.

## Frozen Reporting and Gate

- Report signal/eligibility census, basis at signal/entry/exit, holding time, timeout share, both
  legs, basis PnL, funding PnL, gross/net return, four folds, six symbols, annual cells, cost
  sensitivity, and positive-PnL symbol concentration.
- Cluster bootstrap 10,000 samples by UTC entry date with fixed seed 240024.
- KEEP requires every condition: primary N>=150; expectancy>0; PF>1; clustered 95% lower bound>0;
  at least 3/4 folds positive with N>=20; at least 3/6 symbols positive with N>=20; positive-PnL
  concentration<=45%; reverse N>=50 with expectancy>0 and PF>1; timeout share<=50%; and primary
  expectancy remains positive at 0.30% cost.
- Failure of any condition is REJECT. A pass is only KEEP_FOR_PROSPECTIVE_VALIDATION.

## Frozen Prohibitions

No threshold, lookback, convergence level, timeout, direction, cost, funding rule, universe, fold,
or gate may change after outcome opening. No production, broker, risk, trailing, symbol-admission,
paper-order, or real-order action is authorized.
