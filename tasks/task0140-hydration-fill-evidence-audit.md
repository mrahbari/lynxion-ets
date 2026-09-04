# TASK-0140 — Restart Hydration and Exit-Fill Evidence Audit

**Status:** COMPLETE — IMPLEMENTATION SEQUENCE FROZEN

## Objective

Identify the remaining evidence gaps between TASK-0139's verified stop state and a completed,
cost-adjusted forward position without enabling collection or changing execution behavior.

## Findings

1. Restart hydration already performs one pending-order read and restores the first matching stop
   price, but it discards order identity and emits no `POSITION_HYDRATED` event.
2. Hydration currently selects the first matching stop. The evidence layer must record exactly what
   the existing code selected; changing selection policy is outside this task and would alter risk
   behavior.
3. Broker reconciliation detects position disappearance and reads recent terminal order history.
   It retains order ID and realized PnL for operational handling but drops authoritative fill price,
   executed quantity, fees, trigger price/basis, and fill time from the evidence contract.
4. Reconciliation is a separate component with no observer dependency or position key shared with
   ActivePositionManager. Wiring it before defining stable identity would create unjoinable fills.
5. Runtime remains observer-free. No forward ledger or prospective exit-policy boundary exists.

## Frozen Sequence

1. TASK-0141 may add `POSITION_HYDRATED` to ActivePositionManager using only the existing pending
   order response. It must add no query, retry, mutation, or runtime wiring.
2. A later task must define stable cross-component position identity and characterize which fill,
   fee, and realized-PnL fields are genuinely authoritative in the existing reconciliation payload.
3. Only after those repository-only links pass coverage tests may a separate approval gate consider
   runtime collection and freeze a new prospective boundary.

## Verdict

Do not enable TASK-0139 yet. Stop state is causally observable within one process, but restart and
terminal-fill coverage remain incomplete, so current forward records would not satisfy the frozen
profit-lock data gate.
