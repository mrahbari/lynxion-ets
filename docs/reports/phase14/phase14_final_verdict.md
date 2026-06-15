# Phase 14 — Final Verdict: Funding Information Validation

**Date:** 2026-06-13. Analysis only. **No strategy created or modified, no signals generated, no
parameters/thresholds tuned, no profitability estimated** — per the phase mandate.

## The phase question
> Does funding-rate data contain **repeatable predictive information not already present in OHLCV**,
> worthy of *future* strategy development?

## One-line answer
**Largely NO.** Funding is a clean, persistent, structurally-positive series, but it shows **no broad,
time-stable predictive relationship to forward price returns** over 3 years (correlation ≈ 0; 4 of 5
regimes fail cross-symbol and walk-forward tests). **One narrow exception** — *extreme-negative funding
→ positive 24–72h forward return on BTC and ETH* — is sign-stable across all 4 walk-forward folds and
theory-aligned, but it is single-regime, fails on SOL, and is magnitude-unstable. Classified
**WEAK_INFORMATION**, not PROMISING.

## Effect classification (Task 6)

| Observed effect | Symbols | Evidence | **Class** |
|---|---|---|---|
| **extreme_neg → +fwd return, 24h & 72h** | BTC, ETH | sign-consistent all 4 folds; +0.25–0.68% excess; theory-aligned | **WEAK_INFORMATION** |
| extreme_neg → fwd return | SOL | folds flip sign (+2.95 / −2.65 …) | **UNSTABLE_INFORMATION** |
| extreme_pos → fwd return (contrarian hypothesis) | BTC, ETH, SOL | corr ≈ 0; folds flip; no negative-return signal at all over 3y | **NO_INFORMATION** |
| funding ↔ fwd return, linear/rank (IC) | BTC, ETH, SOL | \|IC\| ≤ 0.032 over 3y; BTC's −0.14 was a 1-yr artifact | **NO_INFORMATION** |
| expansion → fwd return | BTC, ETH, SOL | small, sign-inconsistent across symbols & folds | **NO_INFORMATION** |
| contraction → fwd return | BTC, ETH, SOL | small, sign-inconsistent | **NO_INFORMATION** |
| transition (sign flip) → fwd return | BTC, ETH, SOL | folds flip; ETH negative but isolated | **UNSTABLE_INFORMATION** |
| funding **persistence** (funding→funding, ρ₁≈0.8) | all 24 | strong & stable — but predicts *funding*, not *price* | (robust, but **not** price-predictive) |

**Net:** 1 WEAK, 2 UNSTABLE, 4 NO_INFORMATION across the price-predictive effects. **Zero PROMISING.**

## Why the conclusion is trustworthy (and what nearly fooled it)

- **The 1-year price overlap produced a false positive.** On 2025-06→2026-06 alone, BTC showed a clean
  contrarian funding effect (IC −0.140 @72h, extreme_pos → −0.80% @72h). Extending price to the **full
  3 years collapsed it** (IC −0.027; extreme_pos signal gone). The headline result is robust *because*
  it was run over 3 years and the short-window artifact was caught and discarded — not assumed.
- **Walk-forward is decisive:** only **9/60** regime×horizon×symbol effects are even sign-consistent
  across 4 folds — barely above chance — and the survivors concentrate in `extreme_neg` (BTC/ETH).

## Honest limitations (do not over-read this verdict)

1. **Predictive scope = BTC/ETH/SOL** (the 3 symbols with 3-year aligned price). The other 21 funding
   symbols were profiled for integrity/distribution but **not** tested predictively. "Cross-symbol
   inconsistency" is judged on 3 majors.
2. **Overlapping forward-return windows** inflate apparent stability → the true bar for the WEAK effect
   is *higher* than the sign test implies (i.e. the verdict is, if anything, generous to funding).
3. **No cost / no profitability assessed** (by mandate). The `extreme_neg` excess (+0.25–0.68% over
   24–72h) is *information*, not a tradable edge; whether it clears the ~0.30% round-trip cost used in
   earlier phases is **explicitly not evaluated and not claimed**.
4. **`extreme_pos` is a soft bucket** for several symbols (funding ties at the venue default); the clean
   tail (`extreme_neg`) is also the only one that showed anything.

## Answer to "worthy of future strategy development?"

- **As a standalone alpha: NO.** No broad, repeatable, cross-symbol, cost-unaware-yet-meaningful signal
  exists. Four of five regimes are NO/UNSTABLE information; correlation is ≈ 0.
- **As a narrow, conditional context filter: MARGINAL / WEAK — investigate, do not assume.** The single
  defensible thread is **extreme-negative funding as a contrarian/oversold context on BTC and ETH at the
  24–72h horizon.** Any future work must (a) widen the predictive universe beyond 3 symbols (needs 3-year
  intraday price for more funding symbols), (b) account for overlapping-window autocorrelation with
  proper significance testing, and (c) **demonstrate** it survives realistic cost — none of which is in
  scope here. It is a lead, not an edge.

## Consistency with prior phases

This **confirms and sharpens** Phase 13's caution that "new data ≠ edge." Funding — the #1-ranked,
highest-uniqueness, deepest, never-tested data lever — now *has* been tested for information content and
returns **mostly NO_INFORMATION with one WEAK conditional thread.** Like open interest (oi_footprint →
DIRECTIONAL_NO_GO) before it, high informational uniqueness vs OHLCV did **not** translate into broad
predictive content. The READY = 0 strategy verdict is unaffected (this phase created no strategy and
estimated no profitability).

## Deliverables
`funding_dataset_audit.md` · `funding_statistical_profile.md` · `funding_predictive_analysis.md` ·
`funding_walkforward_validation.md` · this file.
Harness: `scripts/funding_information_analysis.py`; price back-fill: `scripts/extend_price_to_funding.py`.
