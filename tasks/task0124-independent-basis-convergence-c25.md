# TASK-0124 — Independent Basis-Convergence Confirmation C-25

**Status:** IN PROGRESS — PREREGISTERED; OUTCOME UNOPENED

## Objective

Independently confirm or reject the unchanged C-24 direct basis-convergence mechanism on the
disjoint DOGE/LINK/LTC/DOT/AVAX universe.

## Acceptance Criteria

- Follow `tasks/research/edge-candidate-register-v24.md` without post-outcome changes.
- Reuse C-24 mechanics unchanged, parameterizing only paths, candidate identity, five-symbol
  universe, and the preregistered five-symbol breadth denominator.
- Add regression coverage for disjoint universe/protocol identity and unchanged mechanics.
- Emit a deterministic primary/reverse report, apply every frozen gate, and run the full suite.
- A failure closes the family; no production, risk, trailing, symbol, or order mutation.
