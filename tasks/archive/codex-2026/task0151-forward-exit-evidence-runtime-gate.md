# TASK-0151 — Forward Exit-Evidence Runtime Gate

**Status:** ACTIVE — FORWARD-ONLY VST COHORT COLLECTING

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

## Frozen Forward Data Gate

Activation is evidence collection only. No exit-policy outcome or alternative threshold may be
computed until all of the following are satisfied prospectively:

- At least 100 completed VST positions after the recorded activation boundary.
- At least 30 completed positions with an eligible trailing-trigger evaluation before closure.
- At least eight completed UTC weeks, five symbols, and both LONG and SHORT observations; neither
  side may contribute fewer than 15 completed positions.
- At least 95% of completed identities have one unambiguous terminal-order linkage, and at least
  90% have complete authoritative fill price, quantity, realized PnL, fee, and exchange time.
- Every admitted stop mutation has a causal request, response, exchange-visibility result, and
  state-commit chain; gaps remain explicit and cannot be imputed.
- Duplicate event IDs, lifecycle regressions, corrupt records, pre-boundary observations, and
  sensitive fields must all equal zero.
- Coverage is reported by UTC week, symbol, side, exit type, and observer run ID before any policy
  comparison is preregistered.

Failure to meet these gates extends collection; it cannot justify relaxing a threshold after
outcomes are visible. A later exit-policy candidate requires its own frozen hypothesis, costs,
temporal validation, clustered uncertainty, and promotion criteria.

## Non-Goals

No real/paper order, broker mutation, account change, threshold tuning, historical backfill, or
profitability claim is permitted.

## Frozen Deployment and Rollback Checklist

1. Identify the single intended VST PID, launch command, commit, and orchestrator read-only; abort
   if runners are duplicated or identity is ambiguous.
2. Construct one shared observer bundle before background threads while preserving disabled
   defaults elsewhere; run focused and full suites.
3. Record activation UTC and commit before the first event; events at or before it are inadmissible.
4. Reload only the verified VST runner once without changing secrets, account settings, policy, or
   symbol admission.
5. Verify one runner, BingX VST identity, protective-order coverage, writable evidence paths, and
   forward-only valid records read-only.
6. On failure, disable injection and restore the prior launch configuration with one reload. Retain
   but invalidate collected evidence; do not delete or reuse it.

Proposed paths are `data/observability/forward_exit/position_identities.json` and
`data/observability/forward_exit/events/`. They remain unwritten before approval and activation.

## Repository Evidence

- Operator approval was received on 2026-09-05.
- Auto-detection wiring is opt-in and remains disabled unless all frozen environment metadata is
  present; production-orchestrator and existing constructor defaults remain disabled.
- One shared bundle supplies run ID, identity snapshot, forward-boundary-enforcing event observer,
  and activation manifest to both position management and reconciliation.
- Existing/cohort-conflicting manifests fail closed, and events must be strictly after boundary.
- Focused suite: 28 passed. Full repository suite: 836 passed with one optional import-linter skip.
- The operator restarted the runner through the tracked `./lynxion` entry point on 2026-09-05.
  Read-only verification found exactly one auto-detection runner, started at 06:49:11 UTC from
  commit `54d7c9ce2ec38876b6c6541f1cdb7c27038ff038`.
- The activation manifest freezes run ID `task0151-20260905T064911Z`, boundary
  `2026-09-05T06:49:11.585276+00:00`, and `historical_import_allowed=false`.
- The first ledger event is at `2026-09-05T06:49:52.949480+00:00`, strictly after the boundary.
  The identity snapshot and event ledger validate successfully; one `POSITION_OBSERVED` event is
  present and the pre-boundary count is zero. This starts collection but does not satisfy any
  outcome, trailing-performance, or profitability gate.
