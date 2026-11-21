# TASK-0293 — C-35 unresolved-signal orchestration fix

## Scope

Fix the frozen public-only hourly orchestration deadlock exposed by the first prospective signal.
Do not change signal logic, timing, costs, gates, broker state, or trading policy.

## Defect

The pipeline attempted to evaluate and append a new signal before resolving the existing mature
signal. The portfolio guard correctly rejected this with `unresolved portfolio signal already
exists`, preventing the outcome stage from ever running.

## Fix

- Resolve mature outcomes after source verification and before evaluating new decisions/signals.
- While an existing signal is not yet mature, return a successful explicit blocked state instead of
  trying to append a second portfolio signal and aborting the pipeline.
- Preserve the one-unresolved-position portfolio rule and all fail-closed integrity checks.
- Add a regression requiring outcome orchestration to precede signal orchestration.

## Acceptance

- Focused orchestration and outcome tests pass.
- The real pipeline completes all eleven stages while the pending signal is immature, then resolves
  it causally once the frozen exit candle and funding coverage exist.
- No broker, authentication, order, runtime, or policy path is used.

## Verdict

`KEEP — FIRST-SIGNAL PIPELINE DEADLOCK FIXED; OUTCOME TO BE RECORDED CAUSALLY`.

The repaired real pipeline passes all eleven stages and explicitly reports
`blocked_by_unresolved_signal=[XRPUSDT:1789282800]` while the exit candle is immature.
