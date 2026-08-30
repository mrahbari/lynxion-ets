# TASK-0111 — Liquidity-Withdrawal Differential C-19

**Status:** COMPLETE — C-19 REJECTED

## Objective

Evaluate one dynamic L2 hypothesis based on relative four-hour withdrawal of near-book bid and ask
notional.

## Acceptance Criteria

- Freeze and commit the entire protocol before opening C-19 outcomes.
- Align both current and lagged snapshots strictly before their decision anchors with <=5m age.
- Use causal thresholds excluding the current observation.
- Preserve C-18 execution, cost, funding, fold, bootstrap, and concentration mechanics.
- Evaluate once without direction reversal, alternate horizons, deeper-level variants, or slicing.
- No production, broker, risk, trailing, symbol-admission, or order change.

## Result

- Primary: 1,973 trades, -0.3533% funding-inclusive expectancy, PF 0.7720, and day-cluster
  bootstrap 95% CI [-0.5424%, -0.1630%].
- All four folds and both sides were negative; only ETH was positive among six symbols.
- Funding was economically neutral; price-only expectancy was also -0.3532%.
- Temporal reverse: 668 trades, -0.3631% expectancy, PF 0.7368.
- At 0.50% cost, primary expectancy was -0.5533%.
- Frozen verdict: **REJECT**. No direction, horizon, level, or subgroup was changed after opening.
