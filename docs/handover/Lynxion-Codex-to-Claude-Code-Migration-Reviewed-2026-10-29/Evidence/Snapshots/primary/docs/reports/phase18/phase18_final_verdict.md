# Phase 18 — Final Verdict: Cross-Exchange & Lead-Lag Microstructure

**Date:** 2026-06-13. Analysis only. No existing strategy/parameter/threshold/risk/execution modified; no
new strategy created; no profitability assumed or denied. Phases 1–17 not overwritten.

## Classification: **WEAK_EDGE**

*Informative but not deployable.* Cross-exchange / lead-lag microstructure **does** contain real,
cross-symbol-consistent predictive information that single-venue OHLCV lacks — but it is economically
sub-cost and not tradable by this system. This is a materially different result from Phase 17's flat
NO_EDGE: there the information was OHLCV-redundant; here it is genuinely new, just not exploitable.

## Answer to the phase question

> Does market microstructure contain predictive information that OHLCV does not?

**Cross-exchange/lead-lag: YES (informationally) — NO (deployably).**

| Test | New info beyond OHLCV? | Strength | Deployable after cost? |
|---|---|---|---|
| T1 cross-asset (BTC→ETH/SOL) | **No** | co-move is contemporaneous & OHLCV-visible; lead ambiguous | No (0/4 folds) |
| T2 perp-spot | **Yes** | perp-leads-spot (k1≈0.02); basis MR (IC −0.01..−0.05) | No (0/4 folds) |
| **T3 cross-exchange (Binance→MEXC)** | **Yes** | **Binance leads MEXC; dispersion→catch-up IC ≈ +0.10** (strongest in Ph17–18) | No (0/4 folds) |

- The **cross-exchange catch-up (T3)** is the clearest, most cross-symbol-consistent predictive signal the
  whole microstructure program has produced, and it is **genuinely non-OHLCV** (it requires comparing two
  venues — MEXC's own OHLCV cannot produce it).
- **Yet it confers no tradable advantage**: the dispersion that drives it (~0.01–0.025%) is *smaller than
  the spread + 0.30% round-trip cost*; gross expectancy ≈ 0; **0/4 walk-forward folds** on every symbol.
  It is a **latency-arbitrage** effect that lives inside the bid-ask and requires co-located, fee-
  advantaged, sub-minute execution this system does not have.

## Why WEAK_EDGE (not NO_EDGE, not READY)

- **Not READY:** no deployable, cost-surviving, walk-forward-stable edge — 0/4 folds, net ≈ −cost
  everywhere.
- **Not NO_EDGE:** there *is* persistent, cross-symbol-consistent informational content beyond OHLCV
  (T3 dispersion IC ≈ 0.10; perp-leads-spot) — calling it "no information" would misstate the evidence.
- **WEAK_EDGE** captures it exactly: **real microstructure information confirmed, but no tradable edge for
  this system.** The honest gap is *execution capability* (latency/cost), not *information*.

## Replacement policy — DENIED, RETIRED slots remain EMPTY

A RETIRED slot may be filled only if a microstructure signal **(a)** shows a statistically stable **edge**,
**(b)** is not reducible to OHLCV, **(c)** survives walk-forward + cross-symbol, **(d)** is structurally
distinct.

| Condition | T3 cross-exchange catch-up (best candidate) |
|---|---|
| (a) stable **edge** | ❌ stable *information*, but **0/4 folds, net ≈ −cost** → no edge |
| (b) not reducible to OHLCV | ✅ genuinely cross-venue |
| (c) survives WFO + cross-symbol | ❌ fails cost-adjusted WFO (info is cross-symbol, edge is not) |
| (d) structurally distinct | ✅ distinct (cross-venue) |

**(a) and (c) fail → REPLACEMENT DENIED. Both RETIRED slots stay EMPTY.** Stable information that is
sub-cost is not a deployable edge; an empty slot (0 PnL / 0 risk) still strictly dominates.

## Honest scope & non-claims

- This bounds **minute-scale** lead-lag from integrated REST kline data. **Sub-minute / tick-level
  lead-lag — the regime where cross-venue arbitrage actually operates and where the T3 signal would be
  captured — is below this resolution and outside this system's execution reach.** Phase 18 therefore
  **does not claim** there is no HFT-scale edge; it shows the minute-scale, retail-executable version is
  sub-cost. The IC≈0.10 catch-up is evidence that the effect is *real*, not that it is *capturable here*.
- MEXC 1m history retention capped the cross-exchange window at ~29 days (still 41.7k bars/symbol, ample
  for the lead-lag CCF and a 4-fold WFO).
- No profitability claimed in either direction.

## Consistency with prior phases

READY = 0 and the empty RETIRED slots are unchanged. Phase 18 sharpens the program's conclusion: when the
search finally surfaced **real non-OHLCV predictive information** (cross-exchange catch-up), it turned out
to be a **latency-arbitrage micro-effect inside the cost barrier** — consistent with "no deployable edge
for this system" while honestly distinct from "no information exists." The single standing research lead
elsewhere remains the Phase-14 WEAK extreme-negative-funding thread; the new T3 finding is an *execution-
gated* lead, not a tradable strategy.

## Deliverables
`phase18_leadlag_architecture.md` · `cross_asset_leadlag_analysis.md` ·
`cross_exchange_basis_analysis.md` · `leadlag_walkforward_results.md` · this file.
Data: `scripts/fetch_xvenue.py`. Harness: `scripts/phase18_leadlag_analysis.py`. Raw:
`phase18_results.json`.
