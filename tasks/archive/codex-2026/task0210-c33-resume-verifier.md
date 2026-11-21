# TASK-0210 — C-33 resume verifier

## Status

`COMPLETE — OFFLINE VERIFIER READY; COLLECTOR REMAINS STOPPED`

## Boundary

Implement a pure, fail-closed comparison of the read-only audits taken immediately
before resume and after its first complete five-minute interval. Do not start a process,
use the network, alter the ledger, or open candidate outcomes.

## Frozen checks

- Both snapshots must be admitted C-33 `COLLECTING` audits with the same activation
  boundary.
- The pre-resume audit must have zero active sessions and the post-resume audit exactly
  one.
- Exactly one new session and one `STARTED` lifecycle record must be appended.
- The post-resume latest record must be strictly newer.
- No record counter or eligible completed-bucket count may regress.
- The first complete interval must add at least five heartbeats and 30 one-minute
  klines (five minutes across the frozen six-symbol universe).

## Acceptance

Synthetic tests cover a valid resume, session-count and active-session failures, bucket
and record-count regression, and incomplete first-interval liveness. Passing this
verifier confirms append-only collection integrity only; it is not an edge result or
permission to start the collector.
