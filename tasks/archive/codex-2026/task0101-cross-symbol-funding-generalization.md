# TASK-0101 — Cross-Symbol Funding Generalization C-12

**Status:** COMPLETE — REJECTED BY FROZEN GATE

## Objective

Test the C-10 funding relationship on unopened BNB/XRP/ADA conditional samples.

## Acceptance Criteria

- Register/data boundary committed before acquisition.
- Funding files are checksummed and integrity-checked.
- Reuse causal C-10 mechanics without threshold/horizon changes.
- Fold/symbol/severity/cost and funding contribution are separable.
- KEEP FOR FURTHER VALIDATION or REJECT; no production mutation.

## Result

- Funding integrity: 9,671 observations, zero duplicate/rate/range violations; per-file SHA-256
  values are frozen in `data/research/c12/funding/manifest.json`.
- Primary 0.30% cost: 455 trades, +0.5403% expectancy, PF 1.2763, 54.73% wins.
- All four folds were positive with 68/111/116/160 trades; BNB, XRP, and ADA were each
  positive with 161/148/146 trades.
- Maximum positive-PnL symbol concentration was 39.91%, below the frozen 50% ceiling.
- The bootstrap 95% interval was [-0.0549%, +1.1266%]. Its lower bound failed the required
  greater-than-zero condition, so the frozen verdict is **REJECT**.
- Price-only expectancy remained +0.4784%; mean funding contribution was +0.0619%. This is
  diagnostic evidence only and does not change the verdict.

No production strategy, risk rule, symbol list, or order path was changed.
