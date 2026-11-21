# TASK-0190 — Shadow net-floor math

## Scope

Implement only the disconnected price/activation primitives frozen in Exit Policy
Register v1. Do not read cohort outcomes or wire the functions into runtime.

## Result

- Exact +5% net-ROE floor conversion reserves entry fee, expected exit fee, and the
  frozen 0.10% remaining slippage before producing symmetric LONG/SHORT stop prices.
- Candidate activation is inclusive at the single frozen +12% observed-ROE threshold.
- Missing/malformed leverage, non-finite values, negative cost reserves, and invalid
  price-domain results fail closed.
- No event membership, stop crossing, PnL, or outcome was calculated.

## Next

TASK-0191: implement causal shadow state transitions and subsequent-observation crossing
tests, still disconnected and outcome-unopened.
