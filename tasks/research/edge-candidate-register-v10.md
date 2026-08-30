# Edge Candidate Register v10 — C-11 Prospective Severe Funding Rebound

**Status:** PRE-REGISTERED — PROSPECTIVE SHADOW ONLY

**Prospective boundary:** `2026-08-30T09:32:29Z` (`1788082349` epoch seconds).

This candidate is derived from C-10's post-result `severity_ratio >= 2` cell. Only funding
settlements strictly after the boundary may count. Historical C-10/C-11 backfills can warm the
threshold but can never become prospective observations.

## Frozen Signal and Virtual Execution

- Symbols: BTCUSDT and ETHUSDT only.
- At each settlement, calculate the 10th percentile from the preceding 365 funding observations,
  excluding current.
- Require current funding < 0, current <= causal p10, and
  `abs(current) / abs(p10) >= 2.0`.
- One virtual LONG per symbol; ignore signals overlapping an unresolved 24-hour virtual trade.
- Entry is the first exact Binance Futures 15m open strictly after settlement; exit is the open
  96 bars after entry.
- Charge 0.30% round-trip cost and include actual intervening long funding cashflows as
  `-funding_rate`.
- This collector is shadow-only: it must not call any broker, strategy, order, sizing, or
  production execution component.

## Prospective Gate

- Minimum 100 completed trades total and 30 per symbol.
- Positive funding-inclusive expectancy, PF > 1, event-bootstrap 95% CI lower bound > 0, both
  symbols positive, at least three positive chronological quartiles, and neither symbol above
  70% of positive PnL.
- Until the minimum is met, verdict is `COLLECTING`, never KEEP.
- A passing cohort becomes `ELIGIBLE_FOR_OPERATOR_REVIEW`; it does not authorize production.

## Operational Rules

- Ledger updates are idempotent by `symbol:funding_timestamp`.
- Pending observations remain pending until exact exit/funding data are available.
- Missing or malformed public data fails closed and is recorded; no synthetic fill.
- Monitoring is separate from ongoing engineering research and must not block it.
