# Phase 6 — Edge Discovery: Synthesis (free-data exploration complete)

**Date:** 2026-06-11   **Status:** consolidates the Phase-6 discovery program
(steps 1–10). Free-data signal classes are exhausted; this is the closing report
for that phase of work. Honest, evidence-based — no tuning, no curve-fitting.

Predecessor: Phase 5 closed **NOT READY (no demonstrable edge)** and proved the
deficit is in **signal generation**, not execution. Phase 6's job was to *find*
entry edge. See `docs/reports/phase6/PHASE6-BLUEPRINT.md`.

---

## 1. What was built (reusable, version-controlled)

- **Predictive-power harness** (`research/edge_discovery/measurement/`): forward-
  return labelling, IC with Newey-West (HAC) significance, decile-spread, event-
  study, **purged+embargoed** CV, **BH-FDR / deflated-Sharpe** multiple-testing,
  per-symbol + regime-conditional evaluation, promote/archive gate. 13 tests.
- **Hexagonal derivatives ingestion** (funding + open interest): domain port →
  ccxt + CSV/provenance adapters → use case → CLI → container. 7 tests.
- **Research datasets** (untracked): 24-symbol × 3-year funding; 24-symbol × 3-year
  8h OHLCV cache.
- **Discipline**: every hypothesis pre-registered with frozen params; default
  REJECT; cumulative multiple-testing; OOS + cost gate before any reliance.

## 2. The discovery program (steps 3–10)

| step | hypothesis class | universe / data | result |
|---|---|---|---|
| 3 | momentum, reversion, RSI/range, volume, cross-sectional | 3 sym, 1y, 15m | 0 promoted |
| 4 | extreme-reversion (batch-1 lead) | 3 sym, 15m | rejected (non-monotone) |
| 5 | funding-carry | 3 sym, 1y | 0; BTC@4d lead flagged |
| 6 | funding-carry, **wider re-test** | 24 sym, 3y, 8h | BTC@4d lead **falsified** (mean IC −0.003) |
| 7 | cross-sectional / lead-lag | 24 sym, 3y, 8h | 0 promoted (mean IC ≈ 0) |
| 8 | **regime-conditional** | 24 sym, 3y, 8h | **revert_highvol_3** — first breadth lead |
| 9 | OOS + cost gate (the lead) | 24 sym, 8h | OOS weak; **rejected at cost gate** |
| 10 | lower-turnover / longer-hold rescue | 24 sym, 8h | **not rescued** (small-sample mirage) |

**~32 hypotheses across 8 classes. Zero tradeable edge.**

## 3. The one real finding — and why it isn't tradeable

**High-volatility-regime short-horizon reversion (`revert_highvol_3`)** is a
*genuine signal-level effect*: in-sample mean IC **+0.064** with **17/24 symbols
same-sign-and-significant** — by far the broadest signal found. It is, however,
**not tradeable**:
- **OOS:** mean IC +0.080 → **+0.043** (persists directionally, breadth weak, 4/24 sig).
- **Cost gate:** gross **+1.3 bps/trade**, breakeven **1.3 bps**, **net @10 bps = −8.7 bps**.
- **Lower-turnover rescue:** no robust net-positive config; longer holds worsen it
  (reversion front-loads/decays); the eye-catching conviction-only positives were a
  40–308-trade outlier mirage (insignificant t).

This is **Phase-5's lesson reproduced from the signal side**: a real but tiny edge
(~1 bp) cannot survive the ~10 bps transaction-cost cliff. **Signal-level edge ≠
tradeable edge.**

## 4. What this rules out (proven, not suspected)

On **free OHLCV + funding** data for liquid crypto perps, evaluated with rigorous
anti-snooping methodology, the following hypothesis classes carry **no tradeable
edge**: trend/momentum, mean-reversion (incl. RSI/range/extreme), volume-spike,
funding-carry, cross-sectional relative-value, lead-lag, and regime-conditional.
The discipline also **rejected two false leads** (extreme-reversion, funding@4d)
before they could become phantom strategies — the system's most important property.

## 5. What remains (each needs a NEW input, not another free-data variation)

1. **Paid microstructure data** — L2 order book, trade tape, liquidations. The
   order-flow / absorption / sweep hypothesis class is the **one genuinely untested
   edge source** (the named edges Phase-5's micro strategies could never compute).
   **APPROVAL-GATED** (RULE 5 #8, external paid service) — not pursued without sign-off.
2. **Fundamentally different classes** — options-implied / basis term-structure,
   on-chain flows, cross-venue dislocations. Most need paid/specialist data.
3. **Lower-cost execution** — the cost cliff killed the one real signal; a maker-
   only / lower-fee venue or much larger gross edge would change the calculus, but
   no free-data signal produced gross edge near the cost threshold.

## 6. Verdict

**No tradeable edge was discovered in the free-data signal space.** This is a
firm, evidence-based result — consistent with and extending Phase-5: the system is
a trustworthy measurement-and-discovery platform around a universe/feature set
that does not contain demonstrable, cost-surviving entry edge. Continued progress
requires **new data inputs** (microstructure/alternative — approval-gated), not
more iteration on price/funding signals.

**Recommendation:** decide between (a) authorizing paid microstructure data to test
the one untested edge class, or (b) accepting the research-stage conclusion that
this universe/data does not support a profitable system. Either way, the harness,
ingestion, datasets, and discipline built here are the durable foundation for
whatever comes next.

_This synthesis closes the free-data edge-discovery loop. No tuning, no execution
simulation, no curve-fitting was performed at any step._
