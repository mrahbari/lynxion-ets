# Phase 13 Recommendation — Data Edge Discovery

**Date:** 2026-06-13. Analysis only. No strategy changes, no implementations, no optimization, **no
profitability claims.**

## The phase question
> Is the lack of deployable edge primarily caused by limitations of the OHLCV-only data architecture —
> i.e., could additional market data plausibly create information that does not already exist in OHLCV?

## Answer (two parts, evidence-based)

**Part 1 — Yes, the decision architecture is strictly OHLCV-only, and genuinely-new data categories
exist.** The production trade-decision path consumes only OHLCV; non-OHLCV machinery (watchers, CMC,
depth/trade endpoints, an archived funding/OI stack) is inert, fusion-only, unstored, or un-wired
(`data_architecture_audit.md`, `unused_data_inventory.md`). Several categories — **funding rates, open
interest, liquidations, order-book depth, trade flow** — carry information that is **not derivable from
price/volume**, so additional data *could plausibly* create information beyond OHLCV. Market breadth and
cross-asset are OHLCV-derived and therefore do **not** add new information.

**Part 2 — But "OHLCV-only" is NOT demonstrated to be the *primary cause* of READY = 0, and likely is
not the whole story.** The one high-uniqueness category that was actually implemented and tested —
**open interest (oi_footprint)** — returned `DIRECTIONAL_NO_GO`. So at least one instance of "add new
data" has already failed to yield an edge here. The prior phases also showed the failure is broad
(strategy-wide, cross-symbol, net of cost). Therefore the honest framing is: **the OHLCV-only
architecture is a real, plausible *limiter of available information*, but the evidence does not show it
is the primary cause of no-edge — and adding data is not demonstrated to fix it.**

## Recommended categories (≤3) — worthy of FUTURE investigation only

1. **Funding Rates** — highest-value, lowest-effort lever. 3 years × 24 symbols of real 8h funding data
   already sit on disk, fully ingested, **never used**; the ingestion stack to refresh/extend it exists
   (archived). High informational uniqueness vs OHLCV, deep free history, trivially backtestable.
   *It has never been tested* — the clearest "cheap, deep, genuinely-new, untested" opportunity.
2. **Trade Flow (aggressor / cumulative volume delta)** — high uniqueness (OHLCV has volume but not
   aggressor side), backfillable from Binance `aggTrades` (already-vendored ccxt), reducible to a
   per-bar CVD series for tractable backtests. Medium-high effort (new ingestion + store).
3. **Open Interest** — high uniqueness; ingestion already exists; **but** Binance history caps at ~30d
   (backtest-limited without a paid feed) **and oi_footprint already tested it → NO_GO**. Recommended
   *only* with deeper third-party history and a fresh, regime-conditioned test — not a re-run of the
   failed design.

Deliberately **not** recommended near-term: **Liquidations** and **Order-Book Depth** (high uniqueness
but no integrated historical source → backtest-blocked); **Stablecoin/Exchange flows** (on-chain, not
integrated, approval-gated); **Breadth/Cross-Asset** (OHLCV-derived → no new information by definition).

## Constraints honoured
No strategy/parameter/threshold changes; no new strategies or alpha models; no optimization; no
profitability claims. The recommendation identifies where *new information* plausibly exists and is
*backtestable*, explicitly noting that informational uniqueness has already (via OI) failed to convert
to edge — so any future work must *demonstrate* edge, not assume it.

## Bottom line
- The architecture **is** OHLCV-only, and funding / trade-flow / OI are the data categories most likely
  to carry information OHLCV lacks *and* be backtestable from already-integrated sources.
- Whether that information yields a deployable edge is **unproven and not assumed** — the only such test
  run so far (OI) failed. The single most defensible, lowest-cost next experiment (in a future,
  un-frozen phase) is to test the **already-on-disk 3-year funding-rate data**, which has never been used.

## Deliverables
`data_architecture_audit.md` · `unused_data_inventory.md` · `market_data_gap_analysis.md` ·
`data_edge_opportunity_matrix.md` · this file.
