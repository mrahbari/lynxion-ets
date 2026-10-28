# TASK0080 — Pre-Registered Candidate Research

**Status:** PAUSED — candidate hypotheses pre-registered; evaluation awaits Task0079 post-deployment cohort evidence

## Scope

Research a small set of explicitly documented, regime-specific candidates in
shadow/backtest environments. Each hypothesis must be declared before running
its evaluation.

## Acceptance Criteria

- Each candidate names its symbol basket, side, regime, inputs, exit logic, costs, and primary metric.
- Four chronological OOS folds remain isolated from selection.
- Candidate is eligible only with positive net expectancy in at least 3/4 folds, PF > 1, and adequate sample per cell.
- No candidate is wired into live execution in this task.

## Candidate Register

See `tasks/research/edge-candidate-register-v1.md`. Candidates are deliberately
small, liquid, side-separated, and reuse existing signal/exit definitions.
