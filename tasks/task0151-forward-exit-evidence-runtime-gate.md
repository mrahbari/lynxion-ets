# TASK-0151 — Forward Exit-Evidence Runtime Gate

**Status:** BLOCKED — OPERATOR RUNTIME APPROVAL REQUIRED

## Objective

Enable the completed repository-only exit-evidence chain for a strictly forward VST observation
cohort, without changing entry, exit, risk, leverage, trailing, or symbol policy.

## Proposed Minimal Change

1. Wire one `PositionIdentitySnapshot` and one `ExitEventLedger` into the existing VST composition
   root using new forward-only local paths.
2. Freeze a UTC activation boundary before the runtime first observes any event.
3. Reload only the intended VST runner, then verify process count and read-only broker coverage.
4. Validate emitted schemas, causal links, exchange-side stop visibility, and terminal completeness;
   never import historical observations.
5. Keep all policy thresholds unchanged. Collection cannot itself authorize a strategy change.

## Approval Gate

This task changes runtime composition, creates production observation files, and requires a
controlled runner reload. Repository tests cannot authorize it. Explicit operator approval for
this exact deployment boundary is required before implementation or activation.

## Read-Only Composition Preflight

- Both `AutoDetectionOrchestrator` and `ProductionTradingOrchestrator` construct their own
  `BrokerReconciliationService()` inside their reconciliation loops; neither currently receives
  observer dependencies from the container.
- `active_position_manager` is a canonical process singleton created at module import with its
  observer and identity store disabled. It must be configured once before protection threads start,
  not mutated after event collection begins.
- `bootstrap/container.py` is the common construction boundary for both orchestrator variants, but
  the running VST variant cannot be inferred safely from repository configuration alone.
- Local process enumeration is restricted in the current sandbox. Runtime identity and single-runner
  status must therefore be verified during the approved deployment preflight, before any reload.
- The minimal implementation must share one run ID, identity snapshot, and event ledger between the
  active-position manager and the reconciliation service; wiring only one side would leave terminal
  evidence unjoinable.

## Non-Goals

No real/paper order, broker mutation, account change, threshold tuning, historical backfill, or
profitability claim is permitted.
