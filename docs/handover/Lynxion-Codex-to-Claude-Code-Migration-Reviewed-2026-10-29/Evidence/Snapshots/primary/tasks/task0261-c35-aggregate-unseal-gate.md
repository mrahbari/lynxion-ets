# TASK-0261 — C-35 aggregate unseal gate

## Scope

Add a fail-closed coverage checkpoint that can determine when aggregate evaluation is allowed
without reading or reporting economic outcome fields.

## Contract

- Count only complete outcomes with a preceding unique signal.
- Require 240 completed positions across eight UTC weeks, at least 80 positions per side, and at
  least 30 positions in four symbols.
- Report only coverage counts and Boolean minimum gates while evidence is insufficient.
- Do not compute or expose returns, expectancy, PF, drawdown, folds, bootstrap, or concentration.
- `READY_FOR_FROZEN_EVALUATION` authorizes only the separately frozen evaluator, never VST or
  production deployment.

## Evidence

Four focused tests cover empty sealing, full admission, each fail-closed dimension, and malformed
ledger rejection. The live cohort remains sealed with zero completed positions.

## Verdict

`KEEP — MINIMUM COVERAGE UNSEAL GATE READY; LIVE AGGREGATES SEALED`.
