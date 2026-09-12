# TASK-0278 — Exit-shadow post-fee replacement cohort

## Scope

Create a replacement prospective exit-shadow cohort whose boundary is strictly later than the
frozen official BingX fee snapshot. Do not start a runtime, access a broker account, open outcomes,
or import historical observations.

## Evidence

- Run ID: `exit-shadow-20260912T164632Z`.
- Boundary: `2026-09-12T16:46:32Z`, after fee capture at `2026-09-12T16:44:38Z`.
- Commit binding: `734feb5677914a7b2f93a24d7ea2ef5fb60d59c2`.
- Event ledger is zero bytes, has zero events, and matches SHA-256 of empty content.
- Historical import is permanently disabled.

## Verdict

`KEEP — POST-FEE EMPTY COHORT READY; NOT ACTIVATED`.
