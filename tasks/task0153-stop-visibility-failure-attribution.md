# TASK-0153 — Stop Visibility Failure Attribution

**Status:** IN PROGRESS — SOURCE SEMANTICS PARTIALLY ATTRIBUTED

## Objective

Determine why forward evidence records broker-accepted stop replacements that are not subsequently
visible, using repository code, frozen TASK-0151 events, and disconnected tests only. This task is
diagnosis, not authorization to alter production behavior.

## Frozen Questions

1. What exact BingX VST response fields cause `_place_conditional_order` to return `success=true`?
2. Does `get_pending_orders` query the same account/product and normalize the same symbol, side,
   position side, order type, trigger price, and order ID used by the placement path?
3. Can accepted orders be missed because of response-schema differences, price parsing, symbol
   formatting, trigger basis, endpoint timing, retry cadence, or filtering?
4. Are repeated attempts creating distinct accepted orders, replacing one order, or reporting a
   false-positive acceptance before exchange persistence?
5. Are the three explicit price rejections causally separate from the accepted-but-invisible
   failures?

## Evidence Boundary

- Read only the forward activation manifest, identity snapshot, event ledger, existing local logs,
  BingX adapter source, and tests.
- Do not call authenticated broker endpoints, place/cancel/replace an order, reload the runner, or
  change account, strategy, risk, trailing, leverage, or symbol settings.
- Do not infer exchange visibility from `success=true`; only the existing visibility event is
  authoritative for this task.

## Required Output

- Deterministic counts by symbol, request outcome, visibility outcome, attempt, and causal chain.
- Source-level placement-to-query field map and identified semantic mismatches.
- A disconnected reproduction for every supported root-cause claim.
- Verdict `ROOT_CAUSE_CONFIRMED`, `PARTIAL_ATTRIBUTION`, or `INSUFFICIENT_EVIDENCE`.
- If a correction is justified, freeze the smallest separate implementation task and its failure-
  injection tests; do not apply the correction inside this diagnosis task.

## Acceptance Criteria

- Every claim is tied to event/source/test evidence and uncertainty is explicit.
- Rejected-price and accepted-but-invisible paths are not conflated.
- No production artifact, policy, order, broker state, or runtime process is modified.

## Evidence

- Three disconnected tests confirm that code-zero placement can succeed without an order ID,
  pending-order API/transport failures collapse to the same empty list as a genuine empty result,
  and attribute matching can verify an order with no exchange identity.
- The source/evidence verdict is `PARTIAL_ATTRIBUTION`: local observability defects are confirmed,
  but current records cannot distinguish exchange non-persistence from query failure, schema
  mismatch, account/product mismatch, or a genuinely empty order book.
- Detailed evidence: `docs/reports/task0153_stop_visibility_failure_attribution.md`.
