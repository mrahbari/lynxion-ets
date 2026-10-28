# TASK-0207 — Exit-shadow activation-readiness gate

## Scope

Implement a pure local readiness gate over the frozen evaluator, proposed empty cohort,
admitted fee schedule, and supplied VST safety evidence. Do not start a runtime or call
a broker.

## Result

- Every frozen artifact must reproduce the committed hash manifest.
- The proposed cohort must be new, empty, historical-import-disabled, and bound to the
  expected commit, run ID, and UTC boundary.
- An admitted pre-activation fee schedule with a canonical hash is mandatory.
- Supplied safety evidence must state one TESTNET runner, `live_trading=False`, a
  read-only protection check, and zero positions missing stop loss.
- Passing returns only `READY_FOR_CONTROLLED_RUNTIME_REVIEW`; it explicitly authorizes
  neither runtime execution nor broker mutation.

## Current interpretation

The last observed `SOLUSDT`/`XRPUSDT` protection failure would keep this gate `BLOCKED`.
This task does not assume that dated broker state is current and does not refresh it.

## Next

Continue independent repository-safe edge research while waiting for a separately
authorized and successfully verified runtime activation.
