# TASK-0276 — Exit-shadow new empty cohort

## Scope

Create and verify the new prospective cohort required by the preregistered +12% activation/+5%
net-floor exit comparison, without starting a runner, reading a broker, or opening outcomes.

## Contract

- Bind the cohort to commit `5234323` and boundary `2026-09-12T15:41:59Z`.
- Require a unique run ID, zero-byte event ledger, zero events, and SHA-256 of empty content.
- Permanently forbid historical import.
- Require the bound commit to remain an ancestor of HEAD.
- Authorize neither runtime nor broker access.

## Evidence

Three focused tests cover exact empty admission, nonempty/historical-import rejection, and hash or
commit drift. The real cohort passes with zero events.

## Verdict

`KEEP — NEW EMPTY COMMIT-BOUND COHORT READY; NOT ACTIVATED`.
