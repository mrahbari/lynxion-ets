# TASK-0332 — C-33 controlled collector liveness restore

## Scope

Close the exact stale C-33 session after proving no collector process exists, then resume the
already-authorized public-only collector and require one new eligible five-minute bucket. Do not
backfill the outage, alter the frozen protocol, open outcomes, call a broker, or change production
trading.

## Execution

- Read-only process discovery found no C-33 collector process.
- Recovery closed only session `33eb1205-4428-401c-aec8-c5a179dba525` and labelled the missing
  interval `INELIGIBLE_NO_BACKFILL`.
- The public collector started a new session, `8ffd1ef5-5dbb-43eb-ad30-bb89d3bc0d2e`.
- The incomplete bucket at connection time remained ineligible as required.

## Verification

- Focused resume/audit suite: `11 passed`.
- Audit after the first complete interval reports exactly one active session and 23 sessions total.
- Eligible completed buckets increased from 740 to 741.
- Latest public record time is `1789409400939` ms and the ledger remains fresh.
- Audit verdict remains `COLLECTING`; no candidate outcome or economic gate was opened.

## Verdict

`KEEP — C-33 PUBLIC COLLECTION LIVENESS RESTORED; EDGE NOT PROVEN`.
