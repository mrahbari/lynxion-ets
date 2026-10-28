# TASK-0271 — C-35 evaluator preflight wiring

## Scope

Make direct execution of the live aggregate evaluator enforce its hash-bound activation manifest
before reading or opening outcome economics.

## Contract

- Load and verify the aggregate activation manifest inside the CLI path.
- Fail before outcome evaluation if protocol, math, evaluator, unseal gate, thresholds, seed,
  sample count, or prepared commit drifted.
- Refresh the evaluator hash before any live outcome exists.
- Preserve pure synthetic evaluation tests and the live sealed state.

## Evidence

The direct CLI regression passes only through the real activation preflight and returns `SEALED`.
All focused aggregate/preflight tests pass; no live economics opened.

## Verdict

`KEEP — DIRECT AGGREGATE EXECUTION IS PRE-FLIGHTED AND FAIL-CLOSED`.
