# Replacement-Strategy Assessment (Phase 12)

**Date:** 2026-06-13. The mandate permits designing **one** architecture-compatible replacement **only
if** evidence demonstrates a retired slot should be replaced — no replacement is required or to be
forced.

## Decision: ⛔ No replacement designed or recommended.

### Evidence basis
1. **The broader-universe validation produced no READY cell** on any strategy or symbol. The only
   positives were XRP-clustered, back-loaded, high-drawdown single episodes (`asset-class-behavior-report.md`)
   — not a deployable edge.
2. **The Phase-11 replacement candidates** (Short-Term Reversal, Donchian Breakout) were already
   designed, implemented, and validated under the same standards and came back **INVALIDATED**
   (stable-negative net of cost on BTC/ETH/SOL, WFO 0–1/4) — see `new_strategy_validation.md`.
3. **No new architecture-compatible hypothesis is suggested by the evidence.** The one lead (trend/
   momentum-family on XRP) is (a) not a new strategy — it is the *existing* trend_following/momentum on
   one symbol, (b) episodic over a ~41-day window, and (c) high-drawdown. Designing a "new" strategy
   around it would be **curve-fitting to one symbol's one trend** — prohibited and unjustified.

### Why the trigger condition is not met
A replacement is justified only if a candidate's evidence **exceeds the retired strategies** under the
full standard (positive + cross-period stable + regime-consistent + walk-forward, per-symbol). Nothing
on the table clears even the lower bar of "positive and cross-period stable" — the XRP cluster fails
stability (back-loaded, ≥1 negative fold for trend/momentum, large drawdowns) and oi_footprint is
architecturally invalid (never reads OI). The retired slots being *empty* strictly dominates adding any
net-negative or episodic strategy.

### What would change this (out of scope)
- Multi-year history for XRP/DOGE (and the rest of the universe) to test whether the trend/momentum
  signal is *repeatable* across regimes rather than a single episode.
- Data feeds the architecture currently lacks (order-book/microstructure, funding, sufficient OI) or a
  relaxation of the no-tuning constraint.
Neither is available/permitted here, and neither is assumed to succeed.

## Conclusion
The two RETIRED slots remain **EMPTY**. No replacement is designed, implemented, or recommended on the
Phase-12 evidence. (The two Phase-11 candidate adapters remain in the tree as documented negative
results, not deployed.)
