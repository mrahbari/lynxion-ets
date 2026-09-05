# TASK-0152 — Forward Exit Cohort Gate Auditor

**Status:** IN PROGRESS — CORE INTEGRITY AUDITOR COMPLETE

## Objective

Build a read-only, deterministic auditor for TASK-0151's forward VST evidence so collection status
and every frozen admission gate can be evaluated without opening or tuning an exit-policy outcome.

## Inputs

- `data/observability/forward_exit/activation.json`
- `data/observability/forward_exit/position_identities.json`
- `data/observability/forward_exit/events/*.jsonl`
- The frozen coverage gates in `tasks/task0151-forward-exit-evidence-runtime-gate.md`

## Frozen Output Contract

The report must include:

- manifest/run identity, activation boundary, commit, and historical-import flag;
- total and completed identities, trailing-eligible completed identities, completed UTC weeks,
  symbols, side counts, exit-type counts, and observer run IDs;
- terminal-linkage and authoritative terminal-field completeness percentages;
- stop-mutation chain counts split into complete and missing request, response, visibility, or
  state-commit links;
- duplicate event IDs, lifecycle regressions, corrupt records, events at or before the boundary,
  sensitive-field violations, and unknown causal references;
- one verdict: `COLLECTING`, `DATA_INVALID`, or `ELIGIBLE_FOR_POLICY_PREREGISTRATION`.

`COLLECTING` is mandatory while any sample or coverage minimum is unmet. `DATA_INVALID` is mandatory
for any integrity violation. Eligibility only permits a separately preregistered comparison; it
cannot produce KEEP, change thresholds, or authorize deployment.

## Acceptance Criteria

- Pure local reads: no broker, network, execution, strategy, risk, or runtime imports/calls.
- Strictly reject events at or before the manifest boundary and events from another run ID.
- Preserve unknown terminal fields as incomplete; never infer or impute them.
- Validate causal ordering and exact event references before counting a stop chain as complete.
- Deterministic JSON output with tests for empty/partial/eligible cohorts and every invalidity class.
- Running the auditor cannot modify source evidence.

## Non-Goals

No policy comparison, threshold selection, PnL optimization, historical backfill, runtime reload,
order placement, or production change.

## Implementation Evidence

- The first unit adds a standalone local auditor and four tests covering a valid partial cohort,
  strict boundary exclusion, foreign-run exclusion, and corrupt-manifest fail-closed behavior.
- The live read-only audit found 11 identities and 239 valid post-boundary events with no manifest,
  snapshot, boundary, run-identity, schema, causal-reference, or sensitive-field violation.
- The cohort has no completed identities and remains COLLECTING. Full frozen gate computation and
  chain-completeness tests remain pending.
