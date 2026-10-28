# Phase 15 — Final Verdict: Long-History Validation & Replacement Eligibility

**Date:** 2026-06-13. Analysis only. **No strategy logic / thresholds / parameters / risk models /
execution code modified. No profitability assumed; no absence-of-profitability assumed — evidence
decided.**

## The phase question
> Is the remaining uncertainty (READY=0, INCONCLUSIVE=4) caused by **insufficient historical coverage**
> rather than **absence of edge**?

## Verdict: **NO — coverage is not the cause. The uncertainty resolves to absence of edge (directional) and structural un-judgeability (selective).**

Evidence (5 strategies × XRP/DOGE/LINK/BTC/ETH, design-TF, regime-conditioned, cost-adjusted, 4-fold WFO;
longest available history 7–9 years, cross-checked against a 1-year window):

1. **Directional strategies (trend_following, momentum, oi_footprint) — INVALIDATED, decisively.**
   Negative net of cost on **all 5 symbols** (−0.11% to −0.35% per signal), with **4,000–11,000 in-regime
   signals** per cell (no small-sample excuse), win rates 0.37–0.43, and **at best 1 of 4 walk-forward
   folds positive** (never all four). The XRP/DOGE/LINK positives that prior phases held open "pending
   longer data" **collapse** — and collapse already at 1-year scale, not just multi-year.

2. **Selective strategies (mean_reversion, vwap_reversal) — INCONCLUSIVE, but for a now-known structural
   reason.** Over 60k–315k bars they fire 18–75 times total with **0–9 in-regime signals**
   (DOGE/LINK vwap = literally 0 over 3 years of 5-minute data). The inconclusiveness is **intrinsic
   selectivity**, not a coverage gap — multiplying the data 60×–300× did not produce a judgeable sample,
   so more history is proven *not* to help.

3. **1 year is sufficient to reach this verdict.** The 1-year and full-history views agree on every cell
   (all negative, fold-unstable); there are no sign flips. The long-history acquisition confirms the
   result and definitively closes the coverage question — it does not change the answer. (This contrasts
   with Phase-14 funding, where the conclusion *was* window-sensitive; here it is not.)

## Reclassification (Task 6)
- **INVALIDATED (confirmed):** trend_following, momentum, oi_footprint.
- **INCONCLUSIVE (confirmed; structural, not coverage):** mean_reversion, vwap_reversal.
- **READY: none.** Full-suite tally unchanged: **READY 0 / NEEDS_IMPROVEMENT 1 / INCONCLUSIVE 4 /
  INVALIDATED 5 / RETIRED 2** (`strategy_reclassification_v3.md`). Phase-15's contribution is *certainty*,
  not redistribution: the open "episodic positive" and "needs more data" doubts are now closed.

## Replacement Program Extension (Task 7)
**DENIED — both RETIRED slots remain EMPTY.** Gating conditions 1 (architectural gap), 2 (uncovered),
and 5 (validated superiority over the slots) are not met. No candidate demonstrates a positive,
cost-adjusted, walk-forward-stable edge; an empty slot (0 PnL/0 risk) strictly dominates every
known-or-unproven-losing candidate (E11 candidates INVALIDATED; OI NO_GO/untestable; funding only
WEAK and not cost-validated). Details: `replacement_eligibility_review.md`.

## Bottom line
The program's no-edge result is **not an artifact of short history.** With the longest data the system
can obtain — spanning multiple full market cycles — the directional strategies are confirmed edgeless net
of cost, the selective strategies are confirmed structurally un-deployable as-is, and no replacement is
warranted. **READY = 0 stands, now with the coverage hypothesis explicitly tested and rejected.**

## Deliverables
`long_history_validation.md` · `xrp_doge_link_repeatability.md` · `strategy_reclassification_v3.md` ·
`replacement_eligibility_review.md` · this file. Data prep: `scripts/fetch_long_history.py`. Harness:
`scripts/phase15_long_history_validation.py`. Raw results: `phase15_results.json`.

## Constraints honoured
No strategy logic, thresholds, parameters, risk models, or execution code touched. Only data acquisition
(price history) and read-only analysis were performed. No profitability claimed in either direction.
