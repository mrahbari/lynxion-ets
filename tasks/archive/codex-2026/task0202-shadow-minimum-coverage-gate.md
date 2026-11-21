# TASK-0202 — Frozen shadow minimum-coverage gate

## Scope

Implement a metadata-only gate that prevents aggregate paired results from being opened
before every TASK-0189 minimum is satisfied. Do not accept or inspect economic fields.

## Result

- Frozen minima are 100 paired terminals, 30 candidate activations, eight UTC weeks,
  five symbols, 15 LONG, and 15 SHORT positions.
- The aggregate gate opens only when all minima pass simultaneously; otherwise status
  remains `COLLECTING`.
- Input schema admits only identity, symbol, side, terminal time, and activation flag.
  Economic fields, duplicates, malformed sides, non-boolean flags, and non-UTC times
  fail closed.

## Boundary

No prospective record or economic result was read. Tests use synthetic metadata only.

## Next

TASK-0203 freezes aggregate metric, fold, clustered-bootstrap, concentration, drawdown,
and tail-risk evaluation interfaces while leaving results sealed behind this gate.
