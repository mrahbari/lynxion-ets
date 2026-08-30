# TASK-0111 — Liquidity-Withdrawal Differential C-19

**Status:** IN PROGRESS — C-19 PREREGISTERED, OUTCOMES UNOPENED

## Objective

Evaluate one dynamic L2 hypothesis based on relative four-hour withdrawal of near-book bid and ask
notional.

## Acceptance Criteria

- Freeze and commit the entire protocol before opening C-19 outcomes.
- Align both current and lagged snapshots strictly before their decision anchors with <=5m age.
- Use causal thresholds excluding the current observation.
- Preserve C-18 execution, cost, funding, fold, bootstrap, and concentration mechanics.
- Evaluate once without direction reversal, alternate horizons, deeper-level variants, or slicing.
- No production, broker, risk, trailing, symbol-admission, or order change.
