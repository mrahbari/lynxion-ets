# Edge Candidate Register v17 — C-18 Near-Book Depth Imbalance

**Status:** OPENED — C-18 REJECTED

C-18 tests whether an extreme imbalance between aggregated bid-side and ask-side notional within
one percent of the market predicts same-direction price continuation over the next day. This is a
new L2 mechanism and does not reuse the rejected OI continuation or exhaustion rules.

## Frozen Universe and Samples

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Official TASK-0109 five-minute book-depth panel; only frozen levels `-1` and `+1` are used.
- Primary: 2024-01-01 through the last common available timestamp, no later than 2026-08-29.
- Temporal reverse sample: 2023-01-01 through 2023-12-31, subject to exact common availability.
- Native Binance Futures 15m prices and actual funding settlements must pass their existing
  integrity gates before evaluation.
- Condition-aligned price outcomes are unopened at this commit boundary.

## Frozen Signal and Causal Alignment

- Decisions occur at exact four-hour UTC boundaries.
- For each symbol and decision, use the latest complete book snapshot strictly before the decision;
  reject it when its age exceeds five minutes. Never forward-fill across that bound.
- Define near-book imbalance as `(notional_m1 - notional_p1) / (notional_m1 + notional_p1)`.
  Reject a zero/non-finite denominator.
- The extreme threshold is the causal p90 of absolute imbalance over the prior 180 valid decision
  observations for that symbol. The current observation is excluded and 180 observations are
  required.
- Imbalance >= threshold signals LONG; imbalance <= -threshold signals SHORT.
- No price, OI, funding-level, volatility, volume, trend, regime, ranking, persistence, or
  symbol-specific filter is allowed.

## Frozen Execution

- Enter at the exact next 15m open and exit at the exact 24h close.
- Reject overlapping positions per symbol; rejected overlaps are reported.
- Apply actual funding settlements strictly after entry and through exit with correct side sign.
- Round-trip cost scenarios: 0.20%, 0.30% primary, and 0.50%.
- Report primary and reverse samples separately, plus four chronological primary folds, sides,
  symbols, funding contribution, staleness, overlap rejections, and missing-alignment counts.
- Confidence interval: deterministic day-cluster bootstrap with the repository-standard seed and
  resample count.

## Frozen Conjunctive Gate

KEEP requires every condition:

- Primary at 0.30% cost: N >= 600, expectancy > 0, PF > 1, bootstrap 95% lower bound > 0.
- At least 3/4 primary folds are positive with >=120 trades each.
- LONG and SHORT are both positive with >=150 trades each.
- At least four of six symbols are positive with >=80 trades each.
- Maximum positive-PnL symbol concentration <=30%.
- Temporal reverse sample: N >= 250, expectancy > 0, and PF > 1.
- Primary expectancy remains positive at 0.50% cost.

A pass is historical KEEP only. It does not authorize production deployment, risk changes, or
real-money execution. A failure closes this exact hypothesis; post-result subgroups are diagnostic
only and may not be promoted from the same sample.

## Frozen Result

C-18 returned 2,154 primary trades with -0.3568% funding-inclusive expectancy, PF 0.7685, a fully
negative bootstrap interval, and negative expectancy in every fold, side, and symbol. The 2023
temporal reverse sample was also negative (-0.2313%, PF 0.8230, N=726). The conjunctive gate
rejects. Machine-readable output: `docs/reports/edge_candidate_c18_holdout.json`.
