# TASK-0177 — Active forward-exit cohort audit

## Boundary

Read-only audit of the prospective cohort activated at
`2026-09-06T12:27:02.259792+00:00`. Do not change exit thresholds, broker state,
the runner, or production risk settings.

## Evidence

Command:

`python scripts/audit_forward_exit_cohort.py --root data/observability/forward_exit/cohorts/task0156-restart-20260906T121500Z`

- 4,356 prospective events across 14 identities; no terminal positions yet.
- 15 stop-replacement requests produced four accepted and visibility-verified chains.
- Eleven responses were rejected. Six belong to a `UNIUSDT` position that the
  broker reported did not exist; the remaining failures include invalid stop-price
  placement and an invalid timestamp before later retries succeeded.
- Observed replacement latency ranged into minutes (up to about 248 seconds).
- `LINKUSDT` and `BCHUSDT` breakeven replacement attempts were emitted while the
  recorded exchange-leverage ROE was below the frozen 6% trigger. Their events have
  `configured_leverage=null` and `exchange_leverage=5.0`, so leverage provenance or
  trigger attribution is not yet sufficient to explain the decision.
- No schema/integrity violation is reported by the cohort auditor, and every accepted
  mutation has a complete request/response/visibility/commit chain.

## Verdict

`COLLECTING_WITH_EXECUTION_ERRORS`. The profitability gates cannot be evaluated
until terminal observations exist. The errors are evidence against treating the
current exit-management path as proven reliable; they are not evidence that a 5%
profit floor would improve net expectancy.

## Next

TASK-0178: diagnose, from source and recorded events only, (1) trigger leverage
selection, (2) stale/nonexistent-position handling, (3) stop-price validation, and
(4) multi-minute mutation latency. Do not deploy a fix or tune thresholds during
diagnosis.
