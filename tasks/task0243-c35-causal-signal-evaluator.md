# TASK-0243 — C-35 causal signal evaluator

## Scope

Implement the pure C-35 signal decision from supplied public candles. Do not fetch data, inspect
outcomes, resolve virtual positions, authenticate, or connect to any broker/runtime path.

## Implementation

- Enforces the six-symbol universe, exact hourly decisions, 15-minute continuity, causal window
  exclusions, strict prospective decision boundary, compression, breakout, range, volume, and
  deterministic portfolio ranking.
- Freezes true-range and linearly interpolated percentile mechanics before any observation.
- Emits only a virtual schedule (decision, next-open entry, eight-bar exit); it cannot place orders.

## Evidence

Four regressions verify a valid LONG, gap rejection, strict-boundary rejection, and deterministic
range ranking. No C-35 signal or outcome was opened.

## Verdict

`KEEP — CAUSAL SIGNAL CORE READY; COLLECTION AND OUTCOME LOGIC NOT YET ACTIVE`.
