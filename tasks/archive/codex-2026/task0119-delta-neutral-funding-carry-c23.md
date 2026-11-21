# TASK-0119 — Delta-Neutral Positive-Funding Carry C-23

**Status:** COMPLETE — C-23 REJECTED

## Objective

Evaluate whether causally unusual positive funding persists long enough for an unlevered,
equal-notional LONG-spot/SHORT-perpetual carry pair to remain profitable after both-leg costs.

## Acceptance Criteria

- Follow `tasks/research/edge-candidate-register-v22.md` without changes after outcome opening.
- Enforce exact point-in-time spot/perpetual alignment and completed-funding timing.
- Unit-test signal exclusion of current funding, next-open entry, next-settlement exit, funding
  sign/window, overlap rejection, two-leg PnL, two-unit capital normalization, and costs.
- Evaluate primary and reverse periods, four folds, six symbols, clustered bootstrap, cost
  sensitivity, concentration, and every frozen gate.
- Emit a reproducible machine-readable report and run the full suite.
- Do not place orders or mutate production strategy, risk, trailing, or symbol admission.

## Result

- Primary: N=3,407, expectancy -0.1914%, PF=0, clustered CI entirely below zero.
- All four folds and all six symbols were negative after the frozen 0.20% cost.
- Gross capital-normalized carry was only +0.0086% on average: +0.0019% basis and +0.0067%
  next-settlement funding.
- Reverse 2023: N=1,033, expectancy -0.1902%, PF=0.
- Frozen verdict: **REJECT**. No production or execution setting changed.

## Test Evidence

- Five focused regressions cover causal thresholding, exact entry/exit timing, funding sign,
  two-unit capital normalization, missing exact bars, overlap, and cost application.
