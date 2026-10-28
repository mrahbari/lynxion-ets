# TASK-0121 — Delta-Neutral Basis Convergence C-24

**Status:** COMPLETE — C-24 REJECTED

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

## Result

- Primary: N=7, expectancy +0.1038%, PF 139.41, positive clustered CI.
- Sample gate failed (required N>=150); no fold or symbol reached its frozen minimum.
- Reverse: N=2, expectancy +0.0041%, insufficient against the required N>=50.
- Timeout share was 14.29%; expectancy remained barely positive at 0.30% cost.
- Frozen verdict: **REJECT**. Sparse positive observations are not an edge claim and cannot be
  reused with a relaxed dislocation threshold.

## Test Evidence

- Five focused regressions passed for causal p99, next-open/convergence timing, timeout, exact-bar
  failure, overlap, funding sign, leg math, capital normalization, and cost.
