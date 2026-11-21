# TASK-0260 — C-35 outcome orchestration and aggregate sealing

## Scope

Connect verified candle, funding, coverage, and signal ledgers to TASK-0251's pure resolver without
opening any live outcome in this unit.

## Contract

- Resolve only an unresolved append-only SIGNAL with its exact exit-open candle present.
- Require a successful same-symbol funding query covering strictly after entry through exit.
- Re-run both candle and funding integrity gates before resolution.
- Append through the idempotent SIGNAL→OUTCOME state gate only with explicit `--commit-outcomes`.
- Emit counts and `aggregate_economics=SEALED`; never expose expectancy, PF, folds, or return
  aggregates before the frozen C-35 minimum gate.

## Evidence

Four focused tests pass for complete resolution, exit/funding waiting, exact coverage, and already-
completed suppression. The real signal ledger remains absent, so no live outcome was opened.

## Verdict

`KEEP — LIVE OUTCOME ORCHESTRATION READY; AGGREGATES SEALED`.
