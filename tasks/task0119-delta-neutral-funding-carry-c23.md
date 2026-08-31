# TASK-0119 — Delta-Neutral Positive-Funding Carry C-23

**Status:** IN PROGRESS — PREREGISTERED; OUTCOME UNOPENED

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
