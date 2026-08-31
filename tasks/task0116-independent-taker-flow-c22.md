# TASK-0116 — Independent Taker-Flow Confirmation C-22

**Status:** IN PROGRESS — C-22 PREREGISTERED, OUTCOMES UNOPENED

## Objective

Independently confirm or reject the unchanged C-21 taker-flow continuation mechanism on a disjoint
five-symbol universe.

## Acceptance Criteria

- DOGEUSDT, LINKUSDT, LTCUSDT, DOTUSDT, AVAXUSDT only; disjoint from C-21.
- Acquire/checksum native 15m taker-flow before evaluation.
- Reuse C-21 signal, p90/180 causal threshold, 4h window, direction, 24h execution, funding, costs,
  bootstrap, and reporting unchanged.
- Primary 2024-01-01–2026-08-29; reverse 2023-01-01–2023-12-31.
- KEEP gates unchanged except symbol breadth is >=4/5 and concentration <=35%.
- No post-result changes and no production/risk/order mutation.
