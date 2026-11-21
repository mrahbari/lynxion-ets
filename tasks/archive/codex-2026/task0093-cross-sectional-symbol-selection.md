# TASK-0093 — Cross-Sectional Symbol Selection C-05

**Status:** COMPLETE — C-05 REJECTED (INSUFFICIENT ALIGNED UNIVERSE AND NEGATIVE RETURN)

## Objective

Test whether dynamic relative-strength/weakness selection improves cost-adjusted conditional
returns across Lynxion's stored universe, without production mutation.

## Acceptance Criteria

- Register v4 is committed before evaluation output exists.
- Features, liquidity eligibility, ranks, and broad-market context use decision-time data only.
- Entry is next-bar open; fixed-horizon exit and costs are explicit.
- Four chronological folds, LONG/SHORT separation, confidence interval, cost sensitivity, and
  symbol concentration are reported.
- Portfolio/single-symbol limits and fold boundaries are respected.
- Leakage and execution semantics have focused regression tests.
- Decision is KEEP FOR FURTHER VALIDATION or REJECT; production remains unchanged.

## Evidence

The v4 protocol was committed as `56c7d7e` before evaluation output. The evaluator loaded 470
eligible symbol files and enforced contiguous lookbacks/fills, point-in-time liquidity ranks,
next-open entry, four-hour exit, fixed portfolio capacity, fold isolation, and deterministic
cluster-bootstrap confidence bounds. Five focused leakage/execution tests passed; the complete
suite finished with 642 passed and 1 optional layering test skipped.

The stored histories do not form the assumed broad aligned panel. Of 920 epoch-anchored
four-hour decision timestamps, 915 had fewer than the required 30 eligible symbols after the
96-bar contiguous-history rule. Only 9 completed trades remained; 6 fold-boundary observations
were unresolved.

| Metric | Result |
| --- | ---: |
| N | 9 |
| Net expectancy at 0.30% cost | -3.8162% |
| Profit factor | 0.1982 |
| Win rate | 44.44% |
| Cluster-bootstrap 95% CI | [-11.1039%, +1.1229%] |
| LONG expectancy / N | -0.1724% / 6 |
| SHORT expectancy / N | -11.1039% / 3 |
| Max positive-PnL symbol concentration | 57.81% |

Cost sensitivity remains negative at 0.20%, 0.30%, and 0.50%. No fold has 30 observations.

## Decision

**REJECT C-05.** It fails expectancy, PF, confidence, fold sample, side sample, and concentration
gates. The result also proves that the present fragmented candle store is not adequate for a
broad cross-sectional claim. Lowering the preregistered minimum universe after seeing this
result would be threshold chasing, so it is not done.

The next task is to determine whether the existing historical downloader can build a fixed,
aligned, sufficiently long liquid-universe panel without changing the prospective boundary or
using future listing information. No production logic changes are justified.

## Reproduction

```bash
python scripts/evaluate_cross_sectional_candidate_c05.py \
  --output docs/reports/edge_candidate_c05_oos.json
```
