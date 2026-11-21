# TASK-0182 — Bounded stop-retry consumer

## Scope

Consume TASK-0181 classification in the existing stop-sync loop. Repository only;
do not alter thresholds, broker settings, runtime wiring, or limiter capacity.

## Result

- Stale-snapshot and ambiguous exchange rejections now defer immediately to a fresh
  manager evaluation instead of repeating the same stale request three times.
- Invalid/expired timestamp failures receive exactly one newly signed outer retry.
- Adapter/transport exceptions defer rather than multiplying adapter-level retries.
- Response telemetry records classification and retry decision without sensitive data.
- Accepted-order visibility and state-commit invariants are unchanged.

## Next

TASK-0183: implement bounded priority admission in the single global limiter with
deterministic concurrency tests. No capacity increase or deployment.
