# TASK-0096 — Volume-Confirmed Acceleration C-07

**Status:** COMPLETE — C-07 REJECTED

## Objective

Evaluate an orthogonal price/volume/BTC-context hypothesis on the aligned futures panel after
C-06 showed no gross extreme-reversal edge.

## Acceptance Criteria

- Register v6 is committed before evaluation output.
- BTC regime, momentum, non-overlapping acceleration, and relative volume are causal and tested.
- Position capacity, single-symbol state, next-open entry, horizon, folds, and costs are exact.
- Fold/side/symbol/context/volume and confidence results remain separable.
- Explicit KEEP FOR FURTHER VALIDATION or REJECT; no production mutation.

## Evidence

Register v6 was committed as `cc75c1b` before evaluation output. Five focused regressions cover
future mutation, exclusion of current volume from its baseline, next-open/fixed-horizon fills,
single-symbol overlap prevention, and cost application. The full suite completed with 656
passed and 1 optional layering test skipped.

| Metric | Result |
| --- | ---: |
| Completed trades | 8,245 |
| Net expectancy at 0.30% | -0.2834% |
| Profit factor | 0.6331 |
| Win rate | 35.57% |
| Decision-cluster bootstrap 95% CI | [-0.3380%, -0.2291%] |
| LONG expectancy / N | -0.2539% / 4,288 |
| SHORT expectancy / N | -0.3155% / 3,957 |

All four folds are negative, from -0.3281% to -0.2192%. All five traded symbols are negative.
Every relative-volume bucket is negative; even the `>=5x` bucket is -0.1923%. At 0.20% cost,
expectancy remains -0.1834%. Implied aggregate gross expectancy is only +0.0166%, and the
cost-adjusted confidence interval remains entirely below zero.

## Decision

**REJECT C-07.** It fails expectancy, PF, confidence, fold, side, and symbol gates. Abnormal
volume plus acceleration and BTC agreement does not create a cost-surviving four-hour edge.
No production mutation is justified.

## Reproduction

```bash
python scripts/evaluate_volume_acceleration_candidate_c07.py \
  --output docs/reports/edge_candidate_c07_oos.json
```
