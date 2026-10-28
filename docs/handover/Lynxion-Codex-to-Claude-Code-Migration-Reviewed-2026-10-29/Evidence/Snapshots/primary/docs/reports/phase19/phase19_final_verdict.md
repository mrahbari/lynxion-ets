# Phase 19 — Final Verdict: Funding + Microstructure Combined Signal Validation

**Date:** 2026-06-13. Analysis only. No existing strategy/parameter/threshold/risk/execution modified; no
new strategy created; no profitability assumed or denied. Phases 1–18 not overwritten.

## Classification: **WEAK_EDGE**

The funding × microstructure combination carries a **real, cost-surviving, theory-aligned signal on BTC
and ETH** (extreme-negative funding + capitulation selling → 24–72h bounce, net +0.40% to +0.64% @72h),
but it is **inconsistent (fails SOL), walk-forward-fragile (no all-fold-positive cell), and is not
improved by the microstructure component over funding alone.** Informative, not deployable.

## Answer to the phase question

> Does combining funding + microstructure produce a deployable, stable, cross-symbol edge that neither
> component does?

**No.** The combination **reproduces the Phase-14 funding thread and does not strengthen it.**

| Finding | Evidence |
|---|---|
| Combo is **positive/cost-surviving on BTC & ETH** @24–72h | BTC +0.64%, ETH +0.40% net @72h (win 0.50–0.59) |
| Combo **fails on SOL** | −1.15% net @72h (win 0.45) — no cross-symbol generalisation |
| Combo is **walk-forward-fragile** | 0 all-fold-positive cells; BTC/ETH means driven by 1–2 early folds |
| Microstructure **does not beat funding-only** | adding flow helps BTC (+0.12%) but hurts ETH (−0.41%) and SOL — net subtractive |
| Exhaustion combo (extreme-pos + buy-flow) | negative on all 3 — no reversal edge |
| Flow-only | negative on all 3 — no edge without funding |

So combining the two weak signals **did not create a stronger one**: the positive cells are inherited
from funding (Phase 14), the failure mode (SOL, fold-fragility) is inherited too, and microstructure
confirmation is, on balance, noise.

## Why WEAK_EDGE (not READY, not NO_EDGE)

- **Not READY:** fails cross-symbol (SOL strongly negative) and walk-forward stability (no all-fold cell);
  a deployable edge must hold across symbols and out-of-sample. It does not.
- **Not NO_EDGE:** there *is* a real, theory-aligned, cost-surviving positive expectancy on BTC/ETH at
  24–72h — calling it "no information" would understate the evidence.
- **WEAK_EDGE** is exact: the same WEAK funding information as Phase 14, now confirmed under a
  microstructure-combined design and **still** sub-deployable. The combination validated the weakness, it
  did not remove it.

## Replacement policy — DENIED, RETIRED slots remain EMPTY

A RETIRED slot may be filled only if a signal **(a)** shows a statistically stable **edge**, **(b)** is
not reducible to OHLCV, **(c)** survives walk-forward + cross-symbol, **(d)** is structurally distinct.

| Condition | Combined capitulation signal |
|---|---|
| (a) stable edge | ❌ no all-fold-positive cell; means driven by 1–2 folds |
| (b) not reducible to OHLCV | ✅ uses funding + aggressor flow |
| (c) survives WFO + cross-symbol | ❌ fails SOL; fold-fragile |
| (d) structurally distinct | ✅ distinct (regime + flow conditioning) |

**(a) and (c) fail → REPLACEMENT DENIED. Both RETIRED slots stay EMPTY.** A cost-surviving-on-2-of-3,
single-fold-driven signal is not a deployable edge; an empty slot (0 PnL / 0 risk) still dominates.

## Honest scope & non-claims

- The BTC/ETH capitulation result is genuine and theory-consistent (deleveraging/short-crowding bounce)
  and would merit *research* attention — but it is **not** validated as a deployable, cross-symbol,
  out-of-sample edge, and **no profitability is claimed.**
- The sampling (8h funding events, 72h horizon) is overlapping/autocorrelated → effective sample below
  nominal n; this is precisely why cross-symbol + walk-forward (which it fails) are the arbiters, not the
  point estimate.

## Consistency with prior phases

READY = 0 and the empty RETIRED slots are unchanged. Phase 19 closes the "maybe the weak threads combine"
question: **they do not.** The funding capitulation thread remains exactly what Phase 14 called it —
**WEAK and unstable** — and microstructure confirmation neither rescues nor extends it. Combined with
Phase 17 (microstructure alone = NO_EDGE) and Phase 18 (cross-exchange = real but sub-cost), the
non-OHLCV search has now tested funding, flow, liquidity, cross-exchange, lead-lag, and their
combinations — with no deployable edge anywhere.

## Deliverables
`phase19_combined_signal_architecture.md` · `funding_microstructure_interaction.md` ·
`combined_walkforward_validation.md` · this file. Harness:
`scripts/phase19_funding_micro_combined.py`. Raw: `phase19_results.json`.
