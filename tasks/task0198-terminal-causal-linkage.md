# TASK-0198 — Terminal causal linkage implementation

## Scope

Preserve event time and quantity through the disconnected shadow input pipeline and
implement the pure authoritative terminal join. Do not open outcomes or calculate PnL.

## Result

- Bound observations now retain UTC event time, activation run, and position quantity.
- Group identity includes run and quantity in addition to symbol, side, entry, and leverage.
- Terminal evidence must exactly cover positions and be both admitted and complete.
- Run, position, symbol, side, entry, leverage, full quantity, strictly later fill time,
  and globally unique terminal order ID all fail closed on mismatch.
- Realized exit commission is preserved separately from the preregistered expected fee.

## Next

TASK-0199 defines funding linkage and primary/stress slippage inputs before paired outcome
evaluation is permitted.
