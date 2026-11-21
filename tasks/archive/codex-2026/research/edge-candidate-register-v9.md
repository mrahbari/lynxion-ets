# Edge Candidate Register v9 — C-10 Extreme-Negative Funding Rebound

**Status:** PRE-REGISTERED — INDEPENDENT HISTORICAL HOLDOUT ONLY

C-10 follows the archived Phase-14 weak-information lead, but repairs its global-percentile
lookahead and adds complete cost/funding economics. This protocol is frozen before acquisition
or evaluation of pre-2023 funding observations.

## Independent Data

- Price: untouched TASK-0098 Binance Futures 15m holdout, 2020–2022.
- Funding: public Binance Futures `/fapi/v1/fundingRate` for BTCUSDT and ETHUSDT over the same
  requested dates, stored under `data/research/c10/funding/` with manifest/checksums.
- BTC/ETH only. SOL is excluded before evaluation because the prior Phase-14 effect was
  directionally unstable on SOL; this is a hypothesis boundary, not a post-C-10 selection.

## Frozen Signal and Execution

- At each funding settlement, calculate the 10th percentile from the prior 365 funding
  observations for that symbol, excluding current.
- Signal only when current funding is negative and <= that causal rolling percentile.
- Enter LONG at the first exact 15m open strictly after the observed settlement.
- Exit at the open 96 bars after entry (24 hours).
- Ignore overlapping signals while the symbol position remains open.
- Charge 0.30% round-trip execution cost.
- Add actual funding cashflow for every settlement strictly after entry and at or before exit:
  long return contribution is `-funding_rate`. Report price-only and funding-inclusive results.
- Cost sensitivity: 0.20%, 0.30%, and 0.50%; no parameter retuning.

## Validation Gate

- Four chronological folds per symbol; positions cannot cross fold boundaries.
- Report total/fold/symbol, price-vs-funding contribution, event-severity buckets, N,
  expectancy, PF, win rate, payoff, drawdown, and deterministic event bootstrap 95% CI.
- KEEP_FOR_PROSPECTIVE_VST requires funding-inclusive expectancy > 0, PF > 1, CI lower bound
  > 0, at least 3/4 positive folds with >=20 trades each, both BTC and ETH positive with >=30
  trades each, and neither symbol above 70% of positive PnL.
- Otherwise REJECT. Reverse-time confirmation can authorize only a new prospective VST cohort.

## Limitations

Funding cashflow ignores mark-price variation between settlement and exit notionals; using rate
as return is the standard unit-notional approximation. This is independent reverse-time
evidence, not forward OOS production proof.
