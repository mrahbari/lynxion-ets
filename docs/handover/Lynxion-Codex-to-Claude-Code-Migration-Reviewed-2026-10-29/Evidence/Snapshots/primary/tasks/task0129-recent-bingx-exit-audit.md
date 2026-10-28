# TASK-0129 — Recent BingX Exit-Management Forensic Audit

**Status:** COMPLETE — READ-ONLY DIAGNOSTIC (2026-09-01)

## Objective

Audit the latest 50 completed BingX VST positions to determine whether breakeven and trailing-stop
behavior is systematically surrendering favorable excursion, without changing any production,
risk, trailing, symbol-admission, or broker-execution setting.

## Required evidence

- Reconstruct completed positions from authoritative filled entry and reduce-only exit orders.
- Use each position's recorded leverage and public one-minute BingX candles between entry and exit.
- Measure net realized ROE, MFE, MAE, MFE-to-exit giveback, duration, fees, and exit-order type.
- Census exits near the configured fee-buffer/breakeven lock and positions whose MFE crossed +10%
  or +12% ROE before giving back profit.
- Compare the observations with the configured +6% breakeven trigger, +10% trailing trigger,
  0.5% price trail, and 0.35% price fee buffer.
- Separate exchange facts, candle-resolution estimates, code facts, and hypotheses.

## Boundary

- Read-only BingX account/history and public market-data calls only.
- Do not place/cancel/amend orders or invoke any broker execution path.
- Do not tune thresholds from this 50-position sample or claim an edge from it.
- Record any proposed threshold change as a preregistered future validation, not a production fix.
- TASK-0128 remains the primary profitability-research task and resumes after this bounded audit.

## Verdict

`ADD TO REMEDIATION BACKLOG`, not a production threshold change. Under the manager's 10x ROE
model, 23/50 positions crossed an estimated +10% MFE, 19/50 crossed +12%, and 14/50 crossed +10%
but exited below +5% net ROE. Nine of those exits finished between +2% and +5% net ROE. This
supports the operator's concern that favorable excursion is frequently surrendered, but the same
sample must not be used to select a replacement threshold.

Historical `allOrders` returned no leverage value. The 10x view is a sensitivity analysis supported
by all three currently open VST positions reporting 10x and by the manager's hard-coded 10x model;
it is not authoritative per-trade historical leverage. The loaded risk configuration reports a 5x
maximum, which conflicts with the exchange's current 10x positions and requires a separate
fail-closed leverage-admission audit.
