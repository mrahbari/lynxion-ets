# TASK-0095 — Market-Neutral Extreme Reversal C-06

**Status:** COMPLETE — C-06 REJECTED

## Objective

Evaluate C-06 on the integrity-checked aligned futures panel without production mutation.

## Acceptance Criteria

- Register v5 is committed before evaluation output.
- Feature, rolling-threshold, ranking, and fill semantics are point-in-time and tested against
  future mutation.
- Both legs enter next-open, exit after four bars, and include frozen costs.
- Pair/leg metrics, four folds, sides, symbols, confidence interval, dispersion buckets, and
  cost sensitivity remain separable.
- Decision is KEEP FOR FURTHER VALIDATION or REJECT under the frozen gate.

## Evidence

Register v5 was committed in `5719b51` before evaluation output. Five focused regressions prove
future-close mutation isolation, exclusion of current dispersion from its threshold, next-open
entry, four-bar holding, opposite extreme legs, and per-leg cost equivalence. The full suite
completed with 651 passed and 1 optional layering test skipped.

| Metric | Result |
| --- | ---: |
| Completed pairs | 15,810 |
| No-trade decisions | 16,275 |
| Net pair expectancy at 0.30% | -0.2999% |
| Profit factor | 0.1345 |
| Win rate | 16.38% |
| Bootstrap 95% CI | [-0.3072%, -0.2926%] |
| LONG leg expectancy | -0.2841% |
| SHORT leg expectancy | -0.3158% |

All four adequately sampled folds are negative (-0.2950%, -0.3024%, -0.2973%, -0.3050%).
All six symbols are negative. Every dispersion bucket is negative. Cost sensitivity remains
negative at 0.20%, 0.30%, and 0.50%; the difference between 0.20% cost and -0.1999% net
expectancy implies essentially zero gross expectancy rather than a hidden cost-surviving edge.

## Decision

**REJECT C-06.** It fails expectancy, PF, confidence, fold, side, and symbol gates. The broad
sample falsifies the market-neutral extreme-reversal hypothesis under the registered horizon.
No production change is justified.

## Reproduction

```bash
python scripts/evaluate_market_neutral_candidate_c06.py \
  --output docs/reports/edge_candidate_c06_oos.json
```
