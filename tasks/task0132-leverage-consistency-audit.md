# TASK-0132 — Leverage Consistency Audit

**Status:** PLANNED — READ-ONLY BOUNDARY

## Objective

Trace leverage from loaded configuration through sizing, order admission, broker requests, position
hydration, and authoritative exchange state, and determine whether any mismatch fails closed.

## Acceptance Criteria

- Identify every leverage source, default, conversion, broker parameter, and authoritative readback.
- Characterize behavior when configured, requested, cached, and exchange leverage disagree.
- Add focused tests for the verified boundary without changing leverage, strategy, risk thresholds,
  trailing, symbol admission, or broker execution state.
- Record any required correction as a separately scoped implementation task.
- Place no real or paper order and call no broker execution path.
