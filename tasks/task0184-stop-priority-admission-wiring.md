# TASK-0184 — Stop priority-admission wiring

## Scope

Wire TASK-0183 priority admission only to BingX conditional stop mutations. Do not
change global capacity, thresholds, account settings, or runtime state.

## Result

- Conditional stop POSTs use the existing global bucket with FIFO priority and a
  15-second admission deadline.
- Queue timeout fails before any HTTP request and returns a non-sensitive explicit
  failure; the manager defers it through TASK-0182 behavior.
- Queue wait duration is carried into prospective stop-response telemetry.
- Ordinary BingX calls keep their prior blocking, non-priority behavior.

## Next

TASK-0185: independent implementation review, concurrency/failure regressions, and
cohort-boundary/deployment decision. Do not reload the runtime automatically.
