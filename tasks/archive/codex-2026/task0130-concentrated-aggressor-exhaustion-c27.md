# TASK-0130 — Concentrated Aggressor Exhaustion C-27

**Status:** COMPLETE — C-27 REJECTED

## Objective

Evaluate whether causally unusual large-trade concentration combined with strong one-sided BTC
aggression predicts a four-hour reversal that survives realistic friction and temporal validation.

## Acceptance Criteria

- Follow `tasks/research/edge-candidate-register-v26.md` unchanged after outcome opening.
- Unit-test causal threshold exclusion, concentration/imbalance conjunction, reversal direction,
  next-open entry, exact four-hour exit, missing paths, overlap, funding sign, and costs.
- Evaluate the primary and temporal-reverse periods, folds, sides, years, daily-cluster bootstrap,
  monthly concentration, sensitivities, and every frozen gate.
- Produce a deterministic machine report and run the full suite.
- Place no orders and change no production strategy, risk, trailing, symbol-admission, or leverage
  setting.

## Result

- Primary: N=186, expectancy -0.3418%, PF 0.2533, daily-clustered CI [-0.4429%, -0.2402%].
- Every fold, both sides, and both primary years were negative; the result was also negative at
  0.20% and 0.50% round-trip costs.
- Temporal reverse 2024: N=71, expectancy -0.4978%, PF 0.1936.
- Frozen verdict: **REJECT**. No production or execution setting changed.

## Test Evidence

- Five focused pre-outcome regressions passed.
- Full post-outcome suite: 764 passed, 1 optional layering test skipped because `import-linter` is
  not installed locally.
