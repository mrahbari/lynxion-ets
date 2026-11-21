# TASK-0181 — Stop-failure classification primitive

## Scope

Implement and test the pure, side-effect-free error classifier frozen by TASK-0179.
Do not change retry behavior, broker traffic, policy thresholds, or runtime wiring.

## Result

- Position absence, side mismatch, and wrong-side stop-price errors classify as
  `STALE_SNAPSHOT_TERMINAL`.
- Invalid/expired timestamps classify as `TIMESTAMP_RETRYABLE`.
- Unknown and empty failures classify fail-closed as `AMBIGUOUS_TERMINAL`.

## Next

TASK-0182 will consume this classifier in stop synchronization, emit its decision in
prospective telemetry, and prove bounded retry counts. It remains repository-only.
