# TASK-0107 — OI-Confirmed Price Impulse C-16

**Status:** COMPLETE — C-16 REJECTED

## Objective

Evaluate one causal price-impulse continuation hypothesis that directly consumes official
open-interest history and actual funding cashflows.

## Acceptance Criteria

- Commit this protocol before aligning OI with price or evaluating outcomes.
- Test strict pre-decision OI/price alignment and current-observation exclusion.
- Use next-open entry, exact 24h exit, overlap rejection, and actual funding signs.
- Keep primary/reverse, folds, symbols, and sides separable.
- Apply the frozen conjunctive gate without same-sample amendments.
- Do not modify production, risk, symbol eligibility, or order handling.

## Result

- Funding integrity: 31,269 observations across six symbols, zero integrity violations.
- Primary: 2,471 trades, -0.1763% funding-inclusive expectancy, PF 0.8818, and day-cluster
  bootstrap 95% CI [-0.3855%, +0.0367%].
- Every primary fold was negative with 578–657 trades. LONG was effectively flat (-0.0012%),
  while SHORT was -0.4021%; only XRP was positive.
- Price-only expectancy was -0.1673%; mean funding contribution was -0.0090%.
- Expectancy remained negative at 0.20%, 0.30%, and 0.50% costs.
- Reverse-time confirmation was also negative (-0.0970%, PF 0.9519, N=817).
- Frozen verdict: **REJECT**. No diagnostic cell can amend it.

No production, broker, risk, symbol-admission, or order behavior changed.
