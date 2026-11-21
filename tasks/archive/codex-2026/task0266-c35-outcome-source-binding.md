# TASK-0266 — C-35 outcome-to-source binding

## Scope

Recompute every completed C-35 outcome from its exact candle and funding sources before allowing
new resolutions.

## Contract

- Require persisted same-symbol funding coverage across each entry-to-exit interval.
- Re-run the frozen resolver against current verified candle and funding ledgers.
- Require the complete stored outcome, including evidence hash and all cost sensitivities, to equal
  the recomputed canonical result.
- Fail closed on source disappearance or any economic-field drift; do not expose aggregates.

## Evidence

Six focused orchestration tests pass, including economic tampering and lost-coverage rejection.
The empty live outcome ledger passes with zero bindings.

## Verdict

`KEEP — COMPLETED OUTCOMES MUST REMAIN EXACTLY BOUND TO SOURCE EVIDENCE`.
