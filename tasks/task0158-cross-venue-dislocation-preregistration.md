# TASK-0158 — Cross-Venue Perpetual Dislocation Preregistration

**Status:** COMPLETE — FORWARD COLLECTION NOT YET IMPLEMENTED

## Objective

Freeze a read-only, prospective C-32 feasibility and outcome contract before any conditional
cross-venue spread observation is recorded.

## Acceptance Criteria

- Follow `tasks/research/edge-candidate-register-v31.md` unchanged after collection begins.
- Implement the collector separately with disconnected parsing, time-skew, VWAP, append-only,
  boundary, restart, duplicate, and malformed-response tests before its first network run.
- Use only unauthenticated public market data; never instantiate a broker adapter or execution path.
- Do not backfill, calculate a verdict, place orders, or change production configuration.

## Result

The C-32 prospective contract is frozen at epoch `1788669552`. No observations or outcomes were
opened, no collector was run, and no runtime or broker state changed. TASK-0159 must implement and
test the collector without changing the frozen candidate mechanics.
