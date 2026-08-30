# Edge Candidate Register v11 — C-12 Cross-Symbol Funding Generalization

**Status:** OPENED — REJECTED BY FROZEN CONFIDENCE GATE

C-12 tests whether C-10's aggregate extreme-negative funding rebound generalizes to three
symbols whose funding-conditioned outcomes were not evaluated in Phase-14 or C-10. It is
frozen before acquiring their pre-2023 funding.

## Data and Universe

- Price: TASK-0098 15m futures holdout, 2020–2022.
- Funding: public Binance Futures fundingRate for BNBUSDT, XRPUSDT, and ADAUSDT over the same
  frozen dates, isolated under `data/research/c12/funding/`.
- BTC/ETH are excluded because C-10 already opened their result; SOL is excluded because the
  prior Phase-14 effect was known unstable before this task.

## Signal, Execution, and Economics

- Identical to base C-10: current negative funding <= causal rolling p10 of the prior 365
  observations, excluding current.
- LONG at first exact 15m open after settlement; exit 96 bars after entry.
- Ignore per-symbol overlap; enforce four chronological folds per symbol.
- Charge 0.30% round trip and add actual intervening long funding cashflows; sensitivity at
  0.20% and 0.50%.
- Report severity only diagnostically; no severity filter is applied.

## Gate

- Funding-inclusive expectancy > 0, PF > 1, bootstrap lower bound > 0.
- At least 3/4 positive folds with >=30 trades each.
- BNB, XRP, and ADA each positive with >=30 trades.
- No symbol above 50% of positive PnL.
- Passing result is KEEP_FOR_FURTHER_VALIDATION only; it cannot alter production or bypass C-11
  prospective confirmation.

## Limitations

Price paths have been used by earlier non-funding hypotheses, but funding-conditioned event
membership for these three symbols is unopened. Funding notional uses the unit-return
approximation documented in C-10.

## Frozen Result

C-12 produced 455 trades at the primary cost, +0.5403% expectancy, PF 1.2763, four positive
folds, three positive adequately sampled symbols, and 39.91% maximum positive-PnL symbol
concentration. The 95% bootstrap interval was [-0.0549%, +1.1266%], so its lower bound did not
clear zero. Per the preregistered all-conditions gate, C-12 is rejected and cannot alter
production. Full machine-readable output is in `docs/reports/edge_candidate_c12_holdout.json`.
