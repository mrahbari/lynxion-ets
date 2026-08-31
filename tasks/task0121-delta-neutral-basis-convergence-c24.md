# TASK-0121 — Delta-Neutral Basis Convergence C-24

**Status:** IN PROGRESS — PREREGISTERED; OUTCOME UNOPENED

## Objective

Test whether causally extreme positive spot/perpetual basis dislocations converge strongly enough
to clear realistic two-leg costs without directional market exposure.

## Acceptance Criteria

- Follow `tasks/research/edge-candidate-register-v23.md` unchanged after outcome opening.
- Unit-test causal p99 exclusion, exact next-open entry, convergence exit timing, timeout, overlap,
  funding window/sign, leg direction, two-unit capital normalization, and cost application.
- Evaluate primary/reverse periods, folds, symbols, annual cells, clustered bootstrap, timeout,
  concentration, and all frozen gates.
- Produce a deterministic machine report and run the full suite.
- Place no orders and change no production strategy, risk, trailing, or symbol-admission setting.
