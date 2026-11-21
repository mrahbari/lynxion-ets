# TASK-0189 — Preregister prospective net-profit floor

## Result

Created `tasks/research/exit-policy-register-v1.md` before any post-fix outcome exists.
The experiment is paired, shadow-only, cost/funding/slippage adjusted, and excludes all
98 historical exits plus the pre-fix forward cohort.

The candidate is one frozen +12% activation / +5% net floor, not a family of variants.
It competes against the current reviewed policy across temporal, side, breadth,
concentration, uncertainty, drawdown, and tail-risk gates.

## Boundary

No policy code, threshold, runtime, broker state, or existing cohort was changed.
Activation remains blocked on TASK-0185 deployment approval and a new empty cohort.

## Next

After deployment approval and successful post-fix verification, implement the
disconnected shadow evaluator and its causality/execution tests before collecting any
eligible outcome.
