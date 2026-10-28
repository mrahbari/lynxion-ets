# TASK0082 — Decision Dataset & Counterfactual Research Lab

**Status:** PROPOSED — RESEARCH INFRASTRUCTURE ONLY

## Why This Is the Highest-Leverage Leap

Lynxion already has substantial execution, risk, and operational-control
infrastructure. Its bottleneck is not another indicator: it cannot yet answer,
from one canonical point-in-time dataset, whether a decision had predictive
edge, whether execution destroyed it, or whether a rejected decision would have
been better than an accepted one.

This task creates that research capability. It does not change strategy rules,
thresholds, position sizing, risk limits, or live routing.

## Objective

Create a versioned decision dataset that joins:

1. every accepted/rejected signal-census record;
2. the exact point-in-time market and MTF feature snapshot used by the decision;
3. eventual exchange fill, SL/TP, realized PnL, fees, slippage, and exit reason;
4. fixed forward-return labels for rejected signals, computed only after their
   horizons have elapsed.

The result must support counterfactual questions such as: “Would rejected,
high-confidence BTC long signals in trending-up regimes have outperformed the
executed set after costs?”

## Design Constraints

- Immutable append-only source events; derived datasets are versioned and reproducible.
- Event timestamps are UTC and joins use only data available at decision time.
- Higher-timeframe inputs are closed-bar aligned and shifted before joining.
- Labels are explicitly separated from features to prevent lookahead leakage.
- Read-only to the live execution path; failure to collect data cannot alter a trade.
- No feature, candidate, or threshold is promoted from a single exploratory slice.

## Deliverables

- A documented decision-event schema and dataset version identifier.
- A deterministic builder that emits a partitioned research dataset.
- A forward-labeler for 5m, 15m, 1h, and 4h returns plus maximum favorable/adverse excursion.
- A reconciliation report linking executed decisions to trade-journal outcomes.
- A counterfactual report comparing accepted vs rejected signals by strategy,
  side, regime, confidence bucket, and liquid symbol basket.
- Unit tests for timestamp alignment, no-lookahead behavior, idempotency, and
  unmatched-event reporting.

## Acceptance Gate

- 100% of post-deployment executed decisions can be joined to an immutable
  decision record or are explicitly reported as unmatched.
- Dataset builds are deterministic from the same input snapshot.
- A test proves no future candle may enter a feature row.
- Reports are exploratory only; no automatic trade filter or capital allocation
  is allowed from this task.

## Success Definition

This task succeeds even if it proves no edge. Its value is reducing the time and
ambiguity needed to reject bad ideas and identify a narrow, testable candidate.
