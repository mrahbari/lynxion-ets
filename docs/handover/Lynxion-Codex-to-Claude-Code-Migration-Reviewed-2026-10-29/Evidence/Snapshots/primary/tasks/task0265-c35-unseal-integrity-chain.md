# TASK-0265 — C-35 unseal integrity chain

## Scope

Require the aggregate-unseal CLI to pass the full signal/outcome integrity gate before counting
minimum evidence coverage.

## Contract

- Validate signal identity, schedule, provenance and complete matching outcome evidence first.
- Only then count weeks, sides, symbols, and completed positions for minimum unsealing.
- Reject records that merely look coverage-complete but lack frozen provenance fields.
- Preserve aggregate sealing and all frozen strategy/economic gates.

## Evidence

Five focused unseal tests pass, including rejection of coverage-shaped but unproven events. The
empty live ledger passes full integrity and remains sealed.

## Verdict

`KEEP — AGGREGATE UNSEALING IS CHAINED TO FULL EVENT INTEGRITY`.
