# TASK-0132 — Leverage Consistency Audit

**Status:** COMPLETE — FAIL-OPEN P0 VERIFIED

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

## Result

- Configured leverage is not represented in ExecutionIntent, Order, or Position.
- The BingX request does not set leverage and final admission does not compare authoritative
  exchange leverage with the configured 5x ceiling.
- Position hydration drops exchange leverage; ActivePositionManager independently assumes 10x.
- Focused characterization demonstrates that a 10x exchange state does not fail closed against a
  configured 5x maximum.
- No runtime or production setting changed. A separate implementation boundary is required.

Evidence: `docs/LYNXION_LEVERAGE_CONSISTENCY_AUDIT.md`.
