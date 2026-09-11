# TASK-0242 — C-35 boundary contract clarification

## Defect found before first observation

The initial C-35 register simultaneously prohibited pre-boundary candles from entering any feature
and allowed history to warm rolling features. Those clauses were contradictory, so an evaluator
could not implement the 30-day percentile causally and deterministically.

## Frozen correction

Before any collector, signal, or outcome exists, clarify that candles at or before the boundary may
be used only for the fixed rolling warmup. They may never become a decision bar, signal, entry,
exit, or counted outcome. Decision-bar, entry, and exit opens must each be strictly after epoch
`1789087244`.

## Boundary

No signal threshold, window, universe, ranking, horizon, cost, or validation gate changed. No data
was collected or outcome opened. This is a prospective-contract correctness repair, not tuning.

## Verdict

`KEEP — CAUSAL BOUNDARY IS NOW UNAMBIGUOUS BEFORE FIRST OBSERVATION`.

The next task may implement the deterministic evaluator and boundary regressions.
