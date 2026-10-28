# Phase 6 · Work Item 1b — Data-Acquisition Decision

**Date:** 2026-06-11   **Type:** decision document (no procurement performed).
Decides *what data Phase-6 edge discovery needs*, in what priority, and which
items are approval-gated. No data is acquired here.
Parent: `docs/reports/phase6/PHASE6-BLUEPRINT.md`.

## 1. Current data state (the constraint)

- **1-minute OHLCV only**, for **BTC/ETH/SOL**, ~1 year (~525k bars each), stored
  as epoch-seconds CSVs in `data/history/raw/1m/`.
- **Limitations proven in Phase 5:** no microstructure (B12 — sweep/absorption/
  imbalance/OI are stubs/proxies); single resolution; only 3 majors that are
  **0.83-correlated → ~1.25 effective bets** (E-P5.4); long-only realised history
  (B15). This data cannot test most of the hypothesis classes in blueprint §3A.

## 2. Data classes mapped to hypothesis classes

| data class | unlocks (blueprint §3A/§3B) | source type | cost | storage |
|---|---|---|---|---|
| **Funding rate** | carry / positioning | exchange API | **free** | tiny |
| **Open interest** | positioning, real `oi_footprint` | exchange API | **free** | small |
| **Multi-resolution native bars** (1m→1d, not resampled) | regime decomposition, horizon search | exchange API | **free** | small |
| **Wider liquid universe** (top ~20–50 perps) | cross-sectional / relative-value (raises effective-bets) | exchange API | **free** | medium |
| **Liquidation feed** | cascade / stop-hunt signals | exchange WS/vendor | free–paid | medium |
| **Trade tape** (tick prints, aggressor side) | order-flow, sweep, absorption | exchange WS / **vendor** | mostly **paid** | large |
| **L2 order book** (depth snapshots/deltas) | imbalance, absorption, book-pressure | **vendor** | **paid** | **very large** |
| **On-chain / exchange netflows** | structural flow | specialist **vendor** | **paid** | medium |

## 3. Priority (enables-most × availability × cost)

1. **Multi-resolution bars + wider liquid universe** — free, directly enables the
   highest-value, lowest-data-risk hypothesis class (**cross-sectional / relative-
   value**), and structurally fixes the 1.25-effective-bets problem.
2. **Funding + open interest** — free, enables carry/positioning and lets the
   `oi_footprint` hypothesis finally be tested on real OI rather than a `*1.5` stub.
3. **Liquidation feed** — cheap/free where available; enables cascade signals.
4. **Trade tape** — high value for genuine order-flow edges, but mostly paid +
   large storage. **Approval-gated.**
5. **L2 order book** — highest microstructure value but paid + very large storage +
   significant engineering. **Approval-gated**, defer until a free-data signal has
   shown promise.
6. **On-chain** — specialist/paid; lowest priority for an intraday crypto edge.
   **Approval-gated.**

## 4. Approval gate (CLAUDE.md RULE 5 #8 — external paid services)

Items 4–6 (trade tape, L2, on-chain) and any **paid vendor feed** require explicit
user approval before procurement. **Decision: do NOT acquire any paid data without
approval.** Phase-6 begins on **free exchange-API data only** (items 1–3), which is
sufficient to test the cross-sectional and carry hypothesis classes — the
directions with the best ROI and no procurement risk.

## 5. Structural-assumption shift

Stop treating the universe as a few independent directional **long** bets. The
0.83 correlation and long-only history mean Phase-6 should frame edge as
**cross-sectional / relative-value / both-sided** across a wider universe — where
correlation becomes a *feature* (relative mispricing) rather than hidden
concentration risk (B10).

## 6. Data acceptance criteria (quality gates — CLAUDE.md #4/#5/#18)

Any acquired dataset must have: documented provenance, explicit timestamp
semantics (note: current 1m CSVs are **epoch seconds**), no survivorship bias
(include delisted/relisted symbols for the wider universe), no lookahead in
point-in-time fields (funding/OI as known *at* `t`, not revised), and
reproducible ingestion. Same rigor as Phase-5's frozen baselines.

## 7. Decision summary

- **Proceed (no approval needed):** plan ingestion of free exchange-API
  multi-resolution bars, a wider liquid perp universe, funding, and open interest —
  to enable cross-sectional + carry hypotheses under the §1a measurement protocol.
- **Hold for approval:** trade tape, L2 order book, on-chain, and any paid vendor.
- **Not started here:** this is a decision, not an ingestion. Building the ingestion
  pipeline is a separate, later work item, only on authorization.
