# TASK-0328 — Task/document directory separation

## Scope

Enforce the operator's directory rule: task definitions and records remain under `tasks/`, while
durable documentation remains under `docs/`. Do not modify source, configuration, runtime, broker,
research data, evidence, candidate gates, or trading policy.

## Findings and changes

- Verified that the remaining non-numbered files under `tasks/` are genuine task directives,
  epics, or task specifications.
- Removed `tasks/momentum_and_regime_optimization_solutions.md`. It was not a task; it was a stale
  strategy recommendation document containing non-admissible edge claims. Retaining or moving it
  would continue reviewer ambiguity.
- Rebuilt `docs/README.md` as the current documentation index and recorded explicit placement rules.

## Verdict

`KEEP — TASKS AND DURABLE DOCUMENTATION SEPARATED; ONE STALE DOCUMENT REMOVED`.
