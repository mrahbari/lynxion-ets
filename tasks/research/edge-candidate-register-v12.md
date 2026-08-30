# Edge Candidate Register v12 — C-13 Temporal Funding Generalization

**Status:** OPENED — REJECTED

C-13 tests the unchanged C-12 relationship on a later, unopened funding-conditioned period.
The purpose is to distinguish a broad but confidence-inconclusive result from a period-specific
artifact without tuning on C-12.

## Data and Universe

- Price: TASK-0094 native Binance Futures 15m panel, 2023-01-01 through 2026-08-29.
- Funding: public Binance Futures `fundingRate` for BNBUSDT, XRPUSDT, and ADAUSDT over the same
  frozen dates, isolated under `data/research/c13/funding/`.
- Funding-conditioned event membership and outcomes for this universe/period are unopened at
  this boundary.

## Frozen Mechanics

- Current negative funding <= causal rolling p10 of the prior 365 funding observations,
  excluding current.
- LONG at the first exact 15m open after settlement; exit 96 bars after entry.
- Reject per-symbol overlaps; enforce four chronological folds per symbol.
- Add actual intervening long funding cashflows.
- Primary round-trip cost 0.30%; sensitivity 0.20% and 0.50%.
- Severity remains diagnostic only; zero-threshold observations remain explicitly reported.

## Frozen Gate

- Funding-inclusive expectancy > 0, PF > 1, bootstrap 95% lower bound > 0.
- At least 3/4 positive folds, each with >=30 trades.
- BNB, XRP, and ADA each positive with >=30 trades.
- No symbol above 50% of positive PnL.
- Every condition is conjunctive. A pass is `KEEP_FOR_PROSPECTIVE_VST`; otherwise `REJECT`.

## Interpretation Boundary

- C-13 is judged standalone. A pooled C-12+C-13 estimate may be reported only as secondary
  context and cannot rescue a failed standalone gate.
- No thresholds, horizon, cost, universe, or acceptance criteria may change after acquisition.
- No production or risk-control mutation is authorized by this experiment.

## Frozen Result

C-13 returned 628 trades at 0.30% cost with -0.0595% expectancy, PF 0.9555, and bootstrap 95%
CI [-0.3599%, +0.2519%]. Only two folds and one of three symbols were positive. The standalone
conjunctive gate rejects, demonstrating that C-12's positive historical relationship did not
remain stable in 2023–2026. Machine-readable output is in
`docs/reports/edge_candidate_c13_temporal_holdout.json`.
