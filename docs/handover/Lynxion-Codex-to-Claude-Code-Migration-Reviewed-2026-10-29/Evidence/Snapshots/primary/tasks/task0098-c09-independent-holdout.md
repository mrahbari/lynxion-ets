# TASK-0098 — C-09 Independent Pre-2023 Holdout

**Status:** COMPLETE — C-09 REJECTED

## Objective

Acquire an untouched futures panel and test the C-08-derived long/BTC-positive hypothesis
without reusing its discovery folds.

## Acceptance Criteria

- Register v8 and data dates are committed before acquisition/evaluation.
- Dataset is isolated, checksummed, exactly aligned, and integrity-checked.
- Features, threshold, next-open entry, holding horizon, costs, and folds are causal/tested.
- Fold/symbol/context/spread/cost metrics and bootstrap CI remain separable.
- Explicit KEEP FOR PROSPECTIVE VST or REJECT; never direct production promotion.

## Dataset Evidence

The independent acquisition produced 80,516 exact six-way aligned 15m bars, from epoch
`1600066800` through `1672530300`. Every source file and the intersection have zero gaps,
duplicates, nonpositive values, OHLC violations, or out-of-range rows. The per-symbol SHA-256
values are recorded in the isolated TASK-0098 manifest; no TASK-0094 file was overwritten.

## Evaluation Evidence

Ten focused acquisition/evaluator tests passed before evaluation. The final complete suite
finished with 667 passed and 1 optional layering test skipped. C-09 results:

| Metric | Result |
| --- | ---: |
| Completed trades | 135 |
| Net expectancy at 0.30% | -0.3000% |
| Profit factor | 0.8854 |
| Win rate | 41.48% |
| Bootstrap 95% CI | [-1.4048%, +0.8569%] |

Only F2 is positive; F1/F3/F4 are negative. No fold reaches the frozen 50-trade minimum.
Three symbols are non-negative but positive-PnL concentration is 43.98%. At 0.20% cost,
expectancy remains -0.2000%. The near-exact relationship between cost and net expectancy shows
aggregate gross expectancy is effectively zero.

## Decision

**REJECT C-09.** The post-C-08 LONG/BTC-positive clue did not reproduce on independent data.
It fails expectancy, PF, confidence, fold sample/stability, and concentration gates. No VST or
production promotion is authorized.

## Reproduction

```bash
python scripts/evaluate_c09_independent_holdout.py \
  --output docs/reports/edge_candidate_c09_holdout.json
```
