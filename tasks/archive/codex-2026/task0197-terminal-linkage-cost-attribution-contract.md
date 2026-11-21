# TASK-0197 — Authoritative terminal linkage and cost attribution contract

## Scope

Define the minimum fail-closed join between one costed prospective shadow position and
one authoritative terminal fill before any baseline/candidate PnL is evaluated. Do not
open the cohort, inspect outcomes, call a broker, or change runtime behavior.

## Required linkage

An admitted terminal must match the prospective position's:

- activation run and position key;
- normalized symbol and explicit LONG/SHORT side;
- entry price and authoritative leverage;
- full position quantity, with no silent partial-fill aggregation;
- terminal fill time strictly after the last admitted manager observation;
- unique terminal order ID and complete fill price, fill quantity, realized PnL, and
  signed exit commission.

The terminal commission is authoritative for realized baseline attribution. The frozen
pre-activation taker schedule remains the candidate's expected exit-cost reserve; it
must not replace the realized terminal commission. Funding and slippage remain separate
cost components under the TASK-0189 preregistration.

## Gap found

`BoundShadowObservation` currently omits observation time and position quantity even
though both exist in the validated source event. Consequently, the current grouped
input cannot prove temporal ordering or full-quantity terminal linkage. The existing
terminal extractor also admits an incomplete terminal object as `eligible=True` while
marking `terminal_evidence_complete=False`; the future join must require both flags.

## Verdict

`DATA_CONTRACT_BLOCKED — TERMINAL CAUSAL LINKAGE INCOMPLETE`

No outcome may be evaluated by position key alone.

## Next

TASK-0198 minimally preserves event time and quantity in the bound observation, carries
them through grouping, and adds a pure terminal join with mismatch and partial-fill
tests. It must not read the active cohort or calculate returns.
