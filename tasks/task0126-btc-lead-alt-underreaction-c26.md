# TASK-0126 — BTC-Lead / Alt-Underreaction C-26

**Status:** IN PROGRESS — PREREGISTERED; OUTCOME UNOPENED

## Objective

Test whether altcoins that have only partially responded to a causally extreme completed BTC move
continue in BTC's direction strongly enough to clear realistic costs.

## Acceptance Criteria

- Follow `tasks/research/edge-candidate-register-v25.md` unchanged after outcome opening.
- Unit-test exact completed-hour aggregation, causal p95 exclusion, response ratio/direction,
  next-open entry, exact four-hour exit, missing paths, overlap, funding sign, and costs.
- Evaluate primary/reverse periods, sides, folds, symbols, annual cells, clustered bootstrap,
  concentration, cost sensitivity, and every frozen gate.
- Produce a deterministic machine report and run the full suite.
- Place no orders and change no production strategy, risk, trailing, or symbol-admission setting.
