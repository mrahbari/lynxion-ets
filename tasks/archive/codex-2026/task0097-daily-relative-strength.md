# TASK-0097 — Daily Relative-Strength Continuation C-08

**Status:** COMPLETE — C-08 REJECTED

## Objective

Evaluate whether longer-horizon cross-sectional continuation exceeds friction on the aligned
futures panel without modifying production.

## Acceptance Criteria

- Register v7 is committed before evaluation output.
- Relative returns and the rolling spread threshold are causal and mutation-tested.
- Paired entry/exit, costs, daily state, and fold isolation are exact.
- Pair/leg/fold/side/symbol/context/spread/cost results remain separable.
- Explicit KEEP FOR FURTHER VALIDATION or REJECT under the frozen gate.

## Evidence

Register v7 was committed as `b343606` before evaluation output. Five focused regressions cover
future mutation, exclusion of current spread from its rolling threshold, next-open/24-hour
fills, distinct pair legs, and per-leg cost. The complete suite finished with 661 passed and
1 optional layering test skipped.

| Metric | Result |
| --- | ---: |
| Completed pairs | 559 |
| Net expectancy at 0.30% | -0.0738% |
| Profit factor | 0.9124 |
| Win rate | 41.50% |
| Bootstrap 95% CI | [-0.2685%, +0.1341%] |
| LONG leg expectancy | +0.1880% |
| SHORT leg expectancy | -0.3356% |

Only F2 is positive; F1, F3, and F4 are negative. Two of five symbols are non-negative. At
0.20% cost the pair is marginally positive (+0.0262%, PF 1.0335), but it fails at the frozen
realistic 0.30% cost and its primary confidence interval crosses zero. BTC-positive context is
+0.0556%, while BTC-negative context is -0.2314%; these are post-result research clues, not a
license to filter this same sample.

## Decision

**REJECT C-08.** It fails primary expectancy, PF, confidence, fold, side, and symbol gates.
Because the apparent LONG/BTC-positive asymmetry was observed after opening all four folds, it
requires a newly frozen hypothesis and independent data; it may not be promoted or validated
by re-slicing this dataset.

## Reproduction

```bash
python scripts/evaluate_daily_relative_strength_c08.py \
  --output docs/reports/edge_candidate_c08_oos.json
```
