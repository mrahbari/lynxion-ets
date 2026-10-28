# TASK-0208 — C-33 collection liveness incident

## Scope

Audit the public C-33 collector and append-only ledger without restarting any process,
opening outcomes, or changing the frozen candidate.

## Evidence

- Auditor verdict remains `COLLECTING` with 351 eligible completed five-minute buckets.
- Ledger counts: 1,777 heartbeats, 10,686 closed one-minute candles, 3,271 liquidation
  records, and two sessions.
- The latest record is an explicit `ENDED` lifecycle event for session
  `ea472ec7-7c09-41dc-9df5-3cb3003d0e0e` at `2026-09-07T17:47:31.089Z`.
- Process inspection found no active `collect_c33_liquidation_events.py` instance.
- The next frozen checkpoint is 500 buckets; with no active session it cannot advance.

## Verdict

`COLLECTING_BLOCKED — PUBLIC_COLLECTOR_STOPPED`

Existing 351 eligible buckets remain valid. No gap is silently treated as uninterrupted
coverage, and no historical data may fill the stopped interval.

## Boundary

The heartbeat policy forbids starting or reloading a runtime. This task therefore only
records the liveness blocker; it does not relaunch the public collector.

## Next

After a separately permitted collector start, create a new session in the same
append-only forward ledger, verify its first record is strictly after the new start,
and continue toward the frozen 500-bucket checkpoint. Do not merge the stopped gap.
