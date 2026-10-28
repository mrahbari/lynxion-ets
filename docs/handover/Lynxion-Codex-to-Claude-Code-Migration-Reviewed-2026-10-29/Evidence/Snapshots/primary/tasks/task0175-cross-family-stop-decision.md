# TASK-0175 — Cross-Family Synthesis and Historical Stop Decision

**Status:** COMPLETE — STOP CURRENT HISTORICAL PANEL; PROSPECTIVE COHORTS CONTINUE

## Decision

Do not generate another candidate from the currently opened historical panels. No historical
candidate has passed every frozen profitability, uncertainty, temporal, breadth, concentration, and
stress-cost gate. Recombining the same price, volume, funding, OI, depth, basis, positioning, taker
flow, and Spot/perpetual observations would now have a higher risk of data snooping than of producing
credible independent evidence.

This is a stop condition for **candidate generation on the current historical data**, not for the
Lynxion objective. C-11 severe-funding rebound, C-33 forced-liquidation exhaustion, and the forward
exit-management cohort remain active prospective experiments under their frozen gates.

## Cross-family evidence

| Family | Evidence | Decision |
|---|---|---|
| Trend/momentum/relative strength | C-01/02/05/08/09/14/15/26 | No robust cost-adjusted temporal/breadth pass |
| Reversal/volatility/structure | C-04/06/07/27/28 | Repeated negative primary and reverse evidence |
| Funding and basis/carry | C-10/12/13/20/23/24/25 | Positive-looking cells failed uncertainty/stability or were too sparse; family variants closed |
| OI | C-16/17 | Independent impulse and flush mechanisms negative |
| Book/liquidity | C-18/19 | Primary and temporal reverse negative |
| Taker/aggressor flow | C-21/22/27/34 | Single-venue, concentration, and cross-venue variants negative; C-34 CI fully negative |
| Positioning | C-29/30 | Sparse, unstable, concentrated; independent confirmation failed |
| Spot/perpetual price discovery | C-31 | Frozen underreaction state did not occur |
| Cross-venue executable dislocation | C-32 | Data contract blocked before observation |
| Severe funding | C-11 | Prospective only; `COLLECTING`, N=1 |
| Forced liquidations | C-33 | Prospective only; 30-day warmup collecting |

## Admission rule from here

A new historical candidate is admissible only if it brings an independently sourced, point-in-time
dataset with a distinct economic mechanism and a clean unopened outcome boundary. It cannot be a new
threshold, direction, symbol subset, holding period, filter, or combination of the exhausted panels.
The source must be obtainable without secrets, paid services, survivorship reconstruction, or
ambiguous timestamps, and must support realistic costs before preregistration.

## Next unit

TASK-0176 should perform a read-only feasibility review of genuinely new public data families—for
example options volatility/skew, exchange reserve/inflow, or another timestamped venue microstructure
source—and select at most one only if provenance, historical availability, causal timestamps, costs,
and an unopened boundary are defensible. Otherwise it must record `NO_ADMISSIBLE_SOURCE` and leave
the roadmap on prospective C-11/C-33/exit evidence rather than manufacture another hypothesis.
