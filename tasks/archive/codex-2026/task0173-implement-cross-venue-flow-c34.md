# TASK-0173 — Implement C-34 Cross-Venue Flow Evaluator

**Status:** IMPLEMENTED — OUTCOME NOT YET OPENED

Implemented register v33 unchanged with full-file hash enforcement before feature/outcome work,
strict exact 16-bar Spot/futures alignment, prior-only rolling thresholds, opposition and strict
threshold gates, Spot-side direction, exact next-open/24-hour execution, funding boundaries,
overlap/fold handling, costs, daily-cluster bootstrap, and all frozen promotion checks.

Focused regressions cover prior-only thresholds, future-mutation isolation, exact entry/exit and
funding sign/boundary, same-sign rejection, and clustered uncertainty. The evaluator has not been
run against the frozen production research panels in this task, so no result is open yet.

## Next unit

TASK-0174 must independently review the implementation against register v33, run focused and full
tests, and only then open the frozen outcomes once. Any mismatch must be corrected before evaluation.
