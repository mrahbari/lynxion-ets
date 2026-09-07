# TASK-0192 — Shadow lifecycle input binding

## Scope

Implement hash-first, boundary-strict binding from a future post-fix lifecycle snapshot
to disconnected shadow observations. Do not read the active pre-fix cohort or calculate
membership, fills, PnL, or outcomes.

## Result

- Exact source SHA-256, activation commit/run, no-history flag, event schema/order, and
  strictly post-boundary timestamps are mandatory.
- Only `MANAGER_EVALUATED` mark observations bind; the reviewed policy thresholds and
  authoritative 10x leverage must exactly match preregistration.
- Foreign runs, altered thresholds, missing/malformed leverage, non-mark prices,
  duplicate IDs, and corrupt causal chains fail closed.
- Output contains state-machine inputs only and calculates no outcome.

## Next

TASK-0193: add disconnected per-position grouping and fee-source contract, without
opening an active cohort or evaluating results.
