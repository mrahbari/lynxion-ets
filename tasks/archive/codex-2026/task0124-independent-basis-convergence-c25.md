# TASK-0124 — Independent Basis-Convergence Confirmation C-25

**Status:** COMPLETE — C-25 REJECTED; FAMILY CLOSED

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

## Result

- Primary: N=2, both DOGEUSDT, expectancy +0.3117%, no losses.
- Reverse: N=0.
- Sample, fold, symbol-breadth, concentration, PF, and reverse gates failed.
- Frozen verdict: **REJECT**. C-24 plus C-25 close direct basis convergence.
- No production or execution setting changed.

## Test Evidence

- Seven focused C-24/C-25 tests passed before outcome opening, including unchanged mechanics and
  disjoint identity coverage.
