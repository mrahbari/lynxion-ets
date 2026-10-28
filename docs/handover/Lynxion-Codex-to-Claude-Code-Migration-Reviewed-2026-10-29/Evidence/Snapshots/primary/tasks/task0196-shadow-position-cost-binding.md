# TASK-0196 — Shadow position grouping and cost binding

## Scope

Group already validated prospective observations by immutable position identity and
join already admitted entry-fee and fee-schedule evidence. Do not evaluate fills,
terminals, PnL, or candidate outcomes.

## Result

- Global observation sequence must remain strictly increasing.
- Symbol, direction, entry price, and authoritative leverage cannot change within a
  position group.
- Entry-fee evidence must exactly cover the grouped position set; missing and extra
  evidence both fail closed.
- Every position retains its entry order identity, entry cost, expected exit cost,
  canonical fee-schedule hash, and ordered observation tuple.
- Unadmitted or malformed evidence is rejected before the shadow state machine.

## Boundary

No cohort was opened and no exit/fill/PnL was calculated. This is a disconnected input
contract only.

## Next

TASK-0197 defines authoritative terminal-event linkage and cost attribution before any
prospective outcome evaluation.
