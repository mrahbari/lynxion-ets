# TASK-0187 — Pre-deployment forward-cohort audit

## Scope

Read-only audit of the still-running pre-fix cohort while TASK-0185 deployment approval
is pending. Do not reload, query the broker, or mix prospective cohort boundaries.

## New evidence since TASK-0177

- Event count increased from 4,356 to 6,677 and identities from 14 to 16; no terminal
  position has yet been linked.
- Stop requests increased from 15 to 43: 23 accepted and 20 rejected in total.
- Two accepted `NEARUSDT` replacements were not visible by exact identity/attributes;
  a third attempt later returned `position not exist`.
- New stale-price failures include ETH and XRP. XRP repeated six wrong-side stop-price
  failures across two evaluations.
- New stop-response latency remains severe: approximately 23–348 seconds. Accepted
  calls also took multiple minutes, so acceptance does not imply timely protection.
- All 21 visible accepted chains were committed; the structural ledger auditor reports
  no schema/causal violations.

## Verdict

`COLLECTING_WITH_RECURRING_EXECUTION_ERRORS`. This confirms the diagnosed defect is
active in the old runtime and directly contaminates exit-quality measurement. It does
not change the repository-ready verdict for TASK-0185 and does not authorize mixing
old observations into a post-fix cohort.

## Next

Wait for explicit controlled-reload approval. On approval, freeze this audit as the
pre-fix boundary and activate a new empty cohort against the reviewed commit.
