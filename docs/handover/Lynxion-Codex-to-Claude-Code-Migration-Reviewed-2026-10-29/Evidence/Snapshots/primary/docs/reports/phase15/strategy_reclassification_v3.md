# Strategy Reclassification v3 (post long-history validation)

**Date:** 2026-06-13. Analysis only; no strategy modified. Phase-15 re-tested the 5 strategies that
showed any positive evidence, per-symbol on XRP/DOGE/LINK/BTC/ETH, design-TF, regime-conditioned,
cost-adjusted, 4-fold walk-forward. Allowed classes (Task 6): **READY / INCONCLUSIVE / INVALIDATED.**
**READY** requires positive, cost-adjusted, regime-consistent expectancy that is walk-forward-stable
(all folds) on ≥1 symbol — **met by none.** Verdict holds on a 1-year window and is confirmed over 7–9
years (see `long_history_validation.md`).

## The 5 re-tested strategies

| Strategy | v2 | Phase-15 evidence (1yr ≡ multi-yr) | **v3** |
|---|---|---|---|
| **trend_following** | INVALIDATED (XRP/DOGE INCONCLUSIVE-episodic) | Negative on all 5 (−0.11 to −0.21%), n=4k–5.5k in-regime, win 0.37–0.43, ≤1/4 folds +. XRP/DOGE positives **collapsed**. | **INVALIDATED** |
| **momentum** | INVALIDATED (XRP INCONCLUSIVE-episodic) | Negative on all 5 (−0.22 to −0.30%), n=8k–11k, **0/4 folds on every symbol** incl. XRP. | **INVALIDATED** |
| **oi_footprint** | INVALIDATED (architecture; XRP +0.38 4/4 episodic) | Negative on all 5 (−0.15 to −0.35%), ≤1/4 folds. XRP collapsed. OI mechanism stubbed + real OI history caps ~30d → long-history OI test impossible. | **INVALIDATED** |
| **mean_reversion** | INCONCLUSIVE (insufficient sample) | Fires ~37–47×/60–77k bars; **in-regime n=1–9** even over 7–9y. Unjudgeable — but now proven **structural selectivity, not coverage**. | **INCONCLUSIVE** (structural) |
| **vwap_reversal** | INCONCLUSIVE (frequency-starved) | Fires 18–75×/up-to-315k 5m bars; **in-regime n=0–8** (DOGE/LINK = 0 over 3y). Unjudgeable — structural selectivity, not coverage. | **INCONCLUSIVE** (structural) |

## What changed vs v2

- **The three directional strategies are reaffirmed INVALIDATED — and the INCONCLUSIVE-episodic flags on
  XRP/DOGE/LINK are now resolved DOWNWARD.** Prior phases held those positives open "pending longer
  data"; longer data shows they collapse. No upgrade; the residual doubt is closed.
- **The two selective strategies stay INCONCLUSIVE, but their status is recharacterised:** v2 left open
  whether more data would make them judgeable. Phase-15 shows it will not — they are intrinsically
  frequency-starved (in-regime sample did not grow with 60×–300× more bars). They are **unjudgeable as
  implemented**, and additional history is proven not to help.
- **No strategy moved toward READY.** Zero READY survives the longest, most powered test the program can
  run.

## Full-suite tally (v3) — 5 re-tested + unchanged carry-over from v2

The other strategies were not re-tested in Phase 15 (no new positive evidence to revisit); their v2
verdicts stand.

| Class | Strategies | n |
|---|---|---|
| **READY** | — | **0** |
| **INVALIDATED** | trend_following, momentum, oi_footprint *(re-confirmed)*; mtf_trend, sweep_scalper *(v2)* | **5** |
| **INCONCLUSIVE** | mean_reversion, vwap_reversal *(re-confirmed, structural)*; liquidity, volatility_breakout *(v2)* | **4** |
| **NEEDS_IMPROVEMENT** | breakout *(v2)* | **1** |
| **RETIRED** | scalping, crypto_breakout | **2** |

Counts match the phase's stated current state (READY 0 / NEEDS_IMPROVEMENT 1 / INCONCLUSIVE 4 /
INVALIDATED 5 / RETIRED 2). **Phase-15 confirms the distribution rather than changing it** — the value
added is *certainty*: the open "episodic positive" and "maybe needs more data" doubts are now closed.

Replacement assessment for the 2 RETIRED slots → `replacement_eligibility_review.md`.
