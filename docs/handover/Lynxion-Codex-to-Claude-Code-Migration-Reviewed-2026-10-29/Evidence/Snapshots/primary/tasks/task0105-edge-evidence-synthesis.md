# TASK-0105 — Edge Evidence Synthesis and Sequential Research Gate

**Status:** COMPLETE — CURRENT HISTORICAL SEARCH ENVELOPE EXHAUSTED

## Objective

Prevent candidate churn and false discovery after C-01 through C-15 by consolidating evidence
at the mechanism-family level and freezing the admission rules for future hypotheses.

## Acceptance Criteria

- Inventory every completed candidate, its sample boundary, primary result, and verdict.
- Group correlated candidates into mechanism families rather than counting them as independent.
- Distinguish preregistered results, post-result clues, and prospective evidence.
- Define a sequential admission gate for C-16+ before selecting another candidate.
- Prohibit same-sample reslicing and parameter relaxation after failed gates.
- Identify the highest-value next data/mechanism path without changing production.

## Result

- C-01–C-15 were consolidated into five correlated mechanism families; none cleared its frozen
  historical promotion gate.
- Phase 5–20 evidence proves that additional OHLCV, available order-flow/CVD, basis, funding×flow,
  and retail-minute cross-exchange variants would repeat exhausted work.
- The only active evidence path is C-11 prospective funding collection.
- New historical edge work requires a materially new envelope: auditable long-history L2,
  liquidations, or OI; or a fee/latency execution change. Those paths are operator-gated.
- No C-16 is admitted from current data. Full synthesis:
  `docs/reports/c01_c15_evidence_synthesis.md`.
