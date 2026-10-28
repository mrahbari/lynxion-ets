# TASK-0136 — Forward Profit-Lock Candidate Admission Audit

**Status:** COMPLETE — THRESHOLD VARIANT NOT YET ADMITTED

## Objective

Determine whether the operator's proposed `+10% to +12% ROE` trigger with a `+4% to +5% ROE`
profit floor is a distinct, testable edge candidate, and select the minimum next work needed without
changing production exit behavior or reopening the latest 50-position diagnostic outcome.

## Result

- At 10x, the existing 0.5% price trail activated at a +10% ROE peak implies approximately +4.95%
  locked ROE before execution friction: `(1.01 * 0.995 - 1) * 10 = 4.95%`.
- At a +12% ROE peak, the same intended trail implies approximately +6.94% locked ROE before
  friction. At 5x and a +10% ROE peak it implies approximately +7.45%.
- Therefore the proposed `+10/+4-5` policy is not presently a distinct threshold family; it is
  approximately what the existing manager already intends at 10x. The observed giveback can arise
  from evaluation cadence, missing authoritative leverage, stop submission/visibility failure,
  restart state, slippage, or fills and cannot be attributed to the threshold from candle MFE.
- Selecting a nearby `+12/+5` variant from the same 50-position audit would be post-result tuning.
  No exit-policy candidate is admitted until forward event coverage can distinguish intended stop
  math from broker-visible execution.

## Next Work Unit

TASK-0137 must connect the already-tested TASK-0134 event ledger to manager evaluation and stop
lifecycle paths in repository code only. It may add observability but cannot change a trigger,
distance, stop decision, retry, order, account setting, runtime, or prospective boundary. A future
candidate must be preregistered before any covered forward outcomes are opened.

## Safety Boundary

No order, broker endpoint, runtime, strategy, risk, leverage, trailing threshold, or symbol setting
was changed. This audit uses deterministic policy algebra and previously recorded diagnostic facts;
it does not claim profitability.
