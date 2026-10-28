# Edge Validation & Profitability Program

## Objective

Demonstrate one reproducible, cost-adjusted, out-of-sample trading edge, or
conclude that no deployable edge exists. This program does not authorize live
capital deployment, strategy threshold tuning, or changes to risk limits.

## Task Order

1. `task0077-prospective-attribution-integrity.md`
2. `task0078-signal-census.md`
3. `task0079-frozen-baseline-prospective-cohort.md`
4. `task0080-pre-registered-candidate-research.md`
5. `task0081-shadow-promotion-gate.md`
6. `task0082-decision-dataset-and-counterfactual-lab.md`

## Handoff State — 2026-08-13

- TASK0077 and TASK0078 are implemented and unit-verified; they require a
  restarted/deployed runtime to generate the first valid evidence.
- TASK0079 awaits the explicit deployment timestamp and completed new trades.
- TASK0080 is pre-registered and paused until TASK0079 supplies a clean cohort.
- TASK0081 has not started and remains prohibited until a candidate passes OOS evaluation.

## Non-Negotiable Gates

- All evaluations include realized fees and slippage.
- No lookahead, data snooping, or in-sample parameter selection.
- No strategy or risk mutation while the frozen baseline cohort is collecting.
- A profitable aggregate cannot mask a losing side, regime, or single-trade concentration.
- No candidate reaches paper promotion without positive results in at least 3 of 4 OOS folds.
