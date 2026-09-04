# TASK-0138 — Forward Exit Causal-Chain Audit

**Status:** COMPLETE — IMPLEMENTATION BOUNDARY FROZEN

## Objective

Determine whether TASK-0137's runtime-disabled observations are sufficient for a defensible
forward profit-lock comparison, and freeze the smallest next correction without enabling runtime
collection or changing exit behavior.

## Findings

1. Stop acceptance is observable, but `_verify_pending_stop` collapses the exchange readback to a
   boolean. It discards the matched order ID, actual visible stop price, and observation time needed
   for a genuine `STOP_VISIBILITY_VERIFIED` event.
2. Manager state is updated only after that boolean returns true, but the update has no causal event
   linking it to the verified exchange order. A restart-safe `STATE_COMMITTED` claim therefore
   cannot yet be reconstructed from the ledger.
3. Restart hydration reads pending stops and restores local prices, but does not emit
   `POSITION_HYDRATED` or preserve the matched stop order identity.
4. Broker reconciliation independently detects a closed position and finds a recent terminal
   order, but it is not connected to the observer and does not preserve a causal link to the stop
   replacement/evaluation that preceded the fill.
5. The runtime composition root imports the canonical manager singleton directly. No observer or
   production ledger is instantiated, so TASK-0137 remains disabled as intended.

## Frozen Next Boundary

The next implementation task may only:

- return structured visibility evidence from the existing pending-order query without adding a
  query, retry, request, cancellation, or order;
- emit `STOP_VISIBILITY_VERIFIED` or `STOP_VISIBILITY_FAILED` from that existing evidence and emit
  `STATE_COMMITTED` only after the already-existing local state mutation succeeds;
- keep all event emission optional, failure-isolated, and disabled in every composition root;
- add deterministic tests for order identity, visible price, causal linkage, failed visibility,
  unchanged broker-call counts, and observer failure isolation.

Runtime enablement, restart-hydration events, exit-fill integration, prospective boundaries,
threshold selection, and outcome analysis remain separate later gates.

## Verdict

TASK-0137 is necessary but not sufficient for profit-lock inference. Enabling it now would collect
partial evidence that cannot reliably separate broker acceptance from visible protection or local
state commitment. Complete the frozen visibility/state link before any forward collection begins.
