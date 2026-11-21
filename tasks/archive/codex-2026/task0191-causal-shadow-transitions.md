# TASK-0191 — Causal shadow transitions

## Scope

Implement disconnected candidate-policy state transitions without reading event files,
opening membership/outcomes, or wiring runtime.

## Result

- Observations must be strictly ordered and a newly activated/ratcheted stop cannot
  fill on the same observation.
- A subsequent adverse gap fills at the first observed mark, never the requested stop.
- Before +12% activation the candidate mirrors the supplied reviewed-policy stop;
  after activation both the baseline stop and +5% net floor ratchet monotonically.
- LONG and SHORT behavior is symmetric; invalid marks/stops and post-terminal advances
  fail closed.

## Next

TASK-0192: bind lifecycle event schema to the disconnected state machine with hash and
boundary validation, while keeping outcome evaluation closed.
