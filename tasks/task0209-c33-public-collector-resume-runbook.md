# TASK-0209 — C-33 public collector resume runbook

## Status

`COMPLETE — EXECUTED AND VERIFIED BY TASK-0217`

## Boundary

Prepare the exact append-only resume sequence for the unauthenticated public C-33
collector. Do not execute it in this task. No broker, account, order, strategy, risk,
or historical endpoint is involved.

## Preconditions

1. `python scripts/audit_c33_collection.py` passes with verdict `COLLECTING`, exactly
   zero active sessions, and 351 or more eligible buckets.
2. No `collect_c33_liquidation_events.py` process exists.
3. The existing activation manifest still requires C-33, protocol v32, historical
   import false, and the same append-only `data/research/c33/events.jsonl` output.
4. The last ledger record is the explicit prior-session `ENDED` event.
5. Runtime-start prohibition is removed or explicit permission is supplied.

## Resume sequence

1. Start exactly one reviewed resume command:
   `python scripts/resume_c33_liquidation_collector.py --enable-network`.
2. Do not replace, truncate, copy, normalize, or backfill the existing ledger.
3. Require one new unique `STARTED` session record strictly after the prior `ENDED`
   timestamp; all subsequent records must carry that new session ID.
4. After the first complete five-minute interval, rerun the auditor and require exactly
   one active session, no integrity exception, and no decrease in eligible bucket count.
5. Treat every interval between sessions as ineligible; never import historical rows.
6. Continue quietly to the frozen 500-bucket checkpoint unless the process ends or an
   integrity error occurs.

## Fail-closed aborts

- Multiple collector processes, absent/duplicate `STARTED`, manifest drift, ledger
  truncation, pre-boundary record, reused session ID, malformed raw hash, active-session
  count other than one, or bucket-count regression.

## Acceptance

The resume was executed after explicit operator authorization and verified by TASK-0217.
C-33 is again `COLLECTING` toward its frozen 500-bucket checkpoint.
