# TASK-0195 — Pre-activation fee-schedule snapshot contract

## Scope

Implement a pure disconnected admission contract for the expected exit fee used by
the preregistered shadow net-profit floor. Do not query a broker, open outcomes, wire
runtime behavior, or change any trading setting.

## Result

- Admission requires an explicit exchange, perpetual market, account tier, source,
  effective time, capture time, and nonnegative taker fee rate.
- Both schedule timestamps must be UTC and no later than candidate activation; a
  schedule cannot be captured before it became effective.
- The admitted expected exit fee is the supplied taker rate converted to price percent.
- A canonical SHA-256 binds the exact supplied schedule for reproducibility.
- Missing provenance, wrong exchange/market, invalid rates, and post-activation
  schedules fail closed.

## Boundary

This makes the cost input representable but does not supply a real schedule snapshot.
Broker collection remains approval-gated and the prospective shadow outcomes remain
unopened.

## Next

TASK-0196 groups validated observations by position and joins entry-fee plus fee-schedule
evidence without evaluating terminal outcomes.
