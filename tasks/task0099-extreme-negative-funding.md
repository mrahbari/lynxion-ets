# TASK-0099 — Extreme-Negative Funding Rebound C-10

**Status:** IN PROGRESS — PROTOCOL AND DATA BOUNDARY FROZEN

## Objective

Acquire independent BTC/ETH funding and perform the first causal, cost- and funding-inclusive
profitability test of the archived extreme-negative funding lead.

## Acceptance Criteria

- Register v9 is committed before funding acquisition/evaluation.
- Funding pagination, timestamps, ordering, duplicates, range, and checksums are validated.
- Rolling percentile excludes current/future observations.
- Entry follows settlement, overlap/folds are enforced, and actual funding cashflows are added.
- Symbol/fold/severity/cost and price/funding contributions remain separable.
- Explicit KEEP FOR PROSPECTIVE VST or REJECT; no production mutation.
