# TASK-0126 — BTC-Lead / Alt-Underreaction C-26

**Status:** COMPLETE — C-26 REJECTED

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

## Result

- Primary: N=103, expectancy -0.2102%, PF 0.744, CI [-0.6996%, +0.4035%].
- Only one fold was positive; LONG was negative and symbol breadth/sample gates failed.
- Reverse: N=49, expectancy -0.9667%, PF 0.238; every fold, side, and symbol was negative.
- Frozen verdict: **REJECT**. No production or execution setting changed.

## Test Evidence

- Five focused regressions passed before outcome opening for exact hourly aggregation, causal p95,
  response direction, next-open/four-hour execution, missing paths, funding signs, and costs.
