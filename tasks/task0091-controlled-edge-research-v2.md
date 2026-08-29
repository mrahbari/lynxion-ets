# TASK-0091 — Controlled Edge Research v2

**Status:** IN PROGRESS — protocol frozen before evaluation

## Objective

Evaluate candidate C-04 from `tasks/research/edge-candidate-register-v2.md` without modifying
production strategy, execution, risk, sizing, or exit logic. Reuse existing research/backtest
infrastructure and historical data.

## Acceptance Criteria

- Registration commit precedes evaluation output.
- Four disjoint chronological OOS folds.
- BTC/ETH/SOL and BUY/SELL results remain separable.
- Costs are included and zero-cost results are not used for a decision.
- Any missing path-dependent execution fidelity is reported as a limitation, not silently
  treated as deployable evidence.
- Decision is KEEP FOR FURTHER VALIDATION or REJECT; never automatic production promotion.
