# TASK-0188 — Controlled stop-fix deployment runbook

## Status

`READY — EXPLICIT RUNTIME APPROVAL PENDING`

## Boundary

Prepare an exact fail-closed VST-only reload sequence for reviewed commit `48566bd`
plus subsequent evidence-only commits. Do not execute any step in this task.

## Preconditions

1. Working tree clean and `HEAD` recorded immediately before reload.
2. Exactly one Lynxion trading runner exists and its preflight reports VST/testnet with
   `live_trading=False`.
3. Record a final read-only audit of the current pre-fix root
   `data/observability/forward_exit/cohorts/task0156-restart-20260906T121500Z`.
4. Do not stop or restart the independent C-33 public collector.
5. Operator explicitly approves the runtime interruption/reload.

## Controlled sequence after approval

1. Gracefully stop only the identified Lynxion trading-runner PID; verify it exited.
2. Create a new, previously nonexistent cohort directory name containing the UTC
   activation timestamp. Never copy events, identities, or activation metadata from
   the pre-fix root.
3. Resolve the proposed empty root against the exact current `HEAD`, a unique run ID,
   and a UTC boundary using `scripts/resolve_forward_exit_cohort.py`; require state
   `NEW` and `historical_import_allowed=false`.
4. Start the existing production auto-detect launcher with only
   `LYNXION_FORWARD_EXIT_ROOT_OVERRIDE` pointing to that new root. Do not add a strategy,
   risk, leverage, symbol, or trailing override.
5. Verify exactly one runner, VST/testnet preflight, `live_trading=False`, activation
   commit equal to `HEAD`, and event timestamps strictly after the new boundary.
6. Perform a read-only broker protection check: every open perpetual position must
   have an identity-matching visible protective stop. No placement/cancel/amend call.
7. Require new telemetry to show bounded queue admission and failure classification
   before labeling the fix runtime-observed.

## Fail-closed aborts

- More than one runner, live credentials/mode, non-empty proposed root, commit mismatch,
  malformed manifest, missing visible stop, timestamp before boundary, or any attempted
  historical import aborts the sequence.
- On failed startup, do not revive the old cohort under a different commit. Any retry
  receives another new empty root and boundary.
- A missing protective stop is an approval-gated safety incident; do not mutate broker
  state automatically as part of verification.

## Acceptance

Deployment remains incomplete until explicit approval and all post-reload checks pass.
This runbook itself changes no runtime, broker state, or cohort.
