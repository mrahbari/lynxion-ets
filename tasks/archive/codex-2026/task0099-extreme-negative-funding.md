# TASK-0099 — Extreme-Negative Funding Rebound C-10

**Status:** COMPLETE — C-10 REJECTED; PROSPECTIVE LEAD RETAINED

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

## Dataset Evidence

BTC and ETH each produced 3,288 funding observations over 2020–2022. Ordering, duplicates,
range, numeric bounds, and checksums passed with zero integrity violations. Nine focused
funding acquisition and causal/economic evaluator tests passed before the result was opened;
the final suite completed with 676 passed and 1 optional layering test skipped.

## Results

| Metric | Result |
| --- | ---: |
| Completed trades | 254 |
| Funding-inclusive expectancy at 0.30% | +0.2008% |
| Price-only expectancy at 0.30% | +0.1909% |
| Profit factor | 1.1175 |
| Win rate | 49.21% |
| Bootstrap 95% CI | [-0.3977%, +0.7977%] |
| Mean funding cashflow contribution | +0.0099% |

All four folds are positive and adequately sampled. BTC is +0.4087% with PF 1.3207 across 128
trades. ETH is -0.0104% with PF 0.9952 across 126 trades, so the frozen both-symbol condition
fails. The confidence interval also crosses zero. Results remain positive at 0.20% and nearly
flat at 0.50% cost.

The `severity_ratio >= 2` cell is +0.7680% with PF 1.4832 and N=107, but this threshold was
observed after opening the result and is only a prospective hypothesis lead. It cannot rescue
C-10 or be revalidated by slicing the same holdout.

## Decision

**REJECT C-10 under its frozen gate.** Aggregate/fold economics are encouraging, but uncertainty
and ETH instability prevent promotion. Freeze a new high-severity hypothesis and evaluate only
on observations collected after its boundary. No live strategy or order path changes.

## Reproduction

```bash
python scripts/evaluate_extreme_negative_funding_c10.py \
  --output docs/reports/edge_candidate_c10_holdout.json
```
