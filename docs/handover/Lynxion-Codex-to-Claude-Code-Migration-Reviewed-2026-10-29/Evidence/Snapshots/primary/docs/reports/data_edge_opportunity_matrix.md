# Data Edge Opportunity Matrix (Phase 13)

**Date:** 2026-06-13. Ranked by **plausible new-information × backtest feasibility × low effort**, using
only sources the repo already integrates. Score = qualitative composite; **not** a profitability claim.

| Rank | Category | Uniqueness vs OHLCV | Hist. availability | Backtest feasibility | Effort | Net opportunity | Status |
|---|---|---|---|---|---|---|---|
| 1 | **Funding Rates** | High | **High** (3yr×24sym on disk) | **High** | **L** (re-wire archived stack) | ★★★★★ | data present + unused |
| 2 | **Trade Flow (CVD)** | **High** | High (aggTrades backfillable) | Med-High | M-H | ★★★★ | new ingestion needed |
| 3 | **Open Interest** | High | Low (~30d cap) | Med-Low | L (re-wire) | ★★★ | present but short; **already tested → NO_GO** |
| 4 | Market Breadth | Low-Med | Med (from existing OHLCV) | High | L | ★★½ | OHLCV-derived (not new info) |
| 5 | Cross-Asset | Low-Med | High (on disk) | Med (arch-limited) | M | ★★ | OHLCV-derived; per-symbol arch blocks it |
| 6 | Liquidations | High | **None** (no backfill) | **None** | H (paid 3rd-party) | ★★ | high value, backtest-blocked |
| 7 | Order Book Depth | High | **None** (snapshot/stream) | **None** (forward-record only) | H | ★½ | high value, heavy, unbacktestable now |
| 8 | Stablecoin Flows | Med-High | Low (proxy only) | Low | H (on-chain, gated) | ★½ | no integrated source |
| 9 | Exchange Flows | Med-High | **None** | **None** | H (on-chain, gated) | ★ | no integrated source |

## How to read it
- **Top of the matrix = highest *new information* you can actually backtest cheaply.** Funding is #1 by
  a wide margin: maximal uniqueness, deepest free history, already on disk, lowest effort.
- **Uniqueness ≠ feasibility.** Liquidations and order-book depth are *high-uniqueness* but fall to the
  bottom because no integrated source provides usable history (backtest-blocked).
- **Breadth / cross-asset are cheap but low-uniqueness** — they are transformations of OHLCV, so they
  cannot create information that "does not already exist in OHLCV" (the phase's stated test). They are
  regime-context at best.
- **The on-chain categories (stablecoin/exchange flows) have no integrated source** and are flagged
  approval-gated in the archived notes.

## Critical caveat (evidence, not assumption)
- **Open Interest was already implemented and tested** (oi_footprint) and returned `DIRECTIONAL_NO_GO`.
  So at least one "new data" category has *already failed* to produce an edge here — high informational
  uniqueness did **not** translate to a usable edge. This is the strongest evidence that *adding data ≠
  finding edge*, and it tempers the matrix: a high rank means "worth investigating," not "will work."
- **Funding (3yr) has never been tested** despite being on disk — it is the clearest "cheap, deep,
  genuinely-new, untested" lever, which is exactly why it ranks #1 for *future investigation*.

Recommendation (≤3) and the answer to the phase question → `phase13_recommendation.md`.
