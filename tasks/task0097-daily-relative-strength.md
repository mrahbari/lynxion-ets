# TASK-0097 — Daily Relative-Strength Continuation C-08

**Status:** IN PROGRESS — PROTOCOL FROZEN

## Objective

Evaluate whether longer-horizon cross-sectional continuation exceeds friction on the aligned
futures panel without modifying production.

## Acceptance Criteria

- Register v7 is committed before evaluation output.
- Relative returns and the rolling spread threshold are causal and mutation-tested.
- Paired entry/exit, costs, daily state, and fold isolation are exact.
- Pair/leg/fold/side/symbol/context/spread/cost results remain separable.
- Explicit KEEP FOR FURTHER VALIDATION or REJECT under the frozen gate.
