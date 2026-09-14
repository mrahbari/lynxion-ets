# TASK-0331 — C-33 stale-session recovery guard

## Scope

Add the minimum fail-closed mechanism required to close one externally proven-dead C-33 session
before resuming the already-authorized public collector. Do not backfill, alter the protocol, open
outcomes, call a broker, or touch production trading.

## Finding

- C-33 stopped advancing at 740 eligible buckets.
- Its latest record was 4.54 days stale relative to current public C-35 coverage.
- The ledger retained one unclosed session even though a read-only process check found no collector.
- Starting another session directly could make the ledger report multiple active sessions.

## Minimal change

- Added an explicit `--recover-only` mode to the existing resume script.
- Recovery requires the exact stale session ID and an explicit no-process confirmation.
- It accepts exactly one active ledger session, requires at least 15 minutes of staleness, appends
  one `ENDED` lifecycle record, and labels the missing interval `INELIGIBLE_NO_BACKFILL`.
- It cannot start the network collector in the same recovery invocation.

## Verification

Twenty-three focused C-33 resume/audit tests pass, including successful exact-session closure and
fail-closed rejection of a fresh or mismatched session.

## Verdict

`KEEP — REPOSITORY RECOVERY GUARD READY; CONTROLLED PUBLIC RESUME IS NEXT`.
