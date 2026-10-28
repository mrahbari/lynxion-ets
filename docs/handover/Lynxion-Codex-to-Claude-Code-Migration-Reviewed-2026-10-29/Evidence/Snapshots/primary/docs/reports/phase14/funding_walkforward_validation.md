# Phase 14 — Funding Walk-Forward Validation

**Date:** 2026-06-13. Analysis only — no signals, no strategy, no profitability. This file tests
**stability through time** (Task 5): does each regime→forward-return effect hold across independent
sub-periods, or is it driven by one lucky window?

## Method

- For BTC/ETH/SOL the 3-year aligned sample (~3,275 obs each) is split into **4 sequential folds**
  (~9 months each). For every regime × horizon, the conditional mean forward return is recomputed
  **independently per fold**.
- An effect is **sign-consistent** only if all folds with ≥5 observations share the same sign. This is a
  deliberately weak bar (sign, not magnitude) — it asks the minimum question: *does the direction even
  repeat?*
- Focus horizons: 24h and 72h (where any conditional effect appeared in the predictive analysis).

## Headline: 9 / 60 effects sign-consistent across all 4 folds

Across all regime × horizon × symbol combinations, only **9 of 60** hold their sign across every fold —
barely above what noise on 4 folds would produce (a zero-information effect is sign-consistent ≈ 1-in-8
of the time by chance, ≈ 7–8 of 60). **The dataset as a whole shows no broad time-stable structure.**

## The one effect that passes — extreme_neg on BTC & ETH

| Symbol | Regime / horizon | Fold means (%) | Consistent? |
|---|---|---|---|
| **BTC** | extreme_neg 24h | +0.31, +0.92, +0.22, +0.21 | **✅ all + ** |
| **BTC** | extreme_neg 72h | +1.09, +1.78, +0.45, +0.32 | **✅ all + ** |
| **ETH** | extreme_neg 24h | +0.60, +1.33, +0.39, +0.29 | **✅ all + ** |
| **ETH** | extreme_neg 72h | +0.77, +1.53, +1.45, +0.53 | **✅ all + ** |
| SOL | extreme_neg 24h | +0.71, −1.22, −0.16, −0.11 | ❌ flips |
| SOL | extreme_neg 72h | +2.95, −2.65, +0.20, −0.80 | ❌ flips |

- **Extreme-negative funding → positive 24h & 72h forward return is sign-stable across all four
  independent ~9-month folds on both BTC and ETH.** This is the strongest single result in Phase 14:
  the direction repeats out-of-window, it is theory-aligned (short-crowding bounce), and it is the only
  cross-fold-stable effect on the two cleanest symbols.
- **But its magnitude is unstable** (BTC 72h: 1.78% in one fold vs 0.32% in another — a 5× spread), and
  **it fails on SOL** (signs flip across folds). So even the "good" effect is *directionally* repeatable
  but *not* magnitude-stable and *not* universal.

## Everything else is fold-unstable

| Regime / horizon | BTC folds (%) | ETH folds (%) | verdict |
|---|---|---|---|
| extreme_pos 72h | +1.04, +0.21, −0.32, −1.46 | +1.31, −0.20, +0.28, −2.48 | ❌ flips, big neg outlier fold |
| transition 72h | +1.18, +0.59, +0.54, −0.20 | +0.46, −0.11, +0.41, −0.90 | ❌ flips |
| extreme_pos 24h | +0.34, +0.03, −0.09, −0.71 | +0.40, −0.06, +0.14, −0.76 | ❌ flips |

- `extreme_pos` is positive early and **negative in the final (2025-26) fold** — i.e. the apparent
  "contrarian" reading from the 1-year study was *one fold*, not a stable effect (confirms the
  correlation collapse in the predictive file).
- `expansion`, `contraction`, `transition` flip sign across folds on every symbol → no time-stable
  information.
- **SOL is unstable in every regime** (note the 72h fold-1 values of +2.95% / +3.21% / +3.59% — a
  single early-2023 high-vol fold dominates SOL's aggregate numbers; outside it, signs scatter).

## What the walk-forward establishes

1. **The aggregate-window effects in the predictive file are mostly fold artifacts.** Only `extreme_neg`
   (BTC/ETH) survives the most basic out-of-window sign test.
2. **No funding regime is time-stable on all three majors.** Cross-symbol generalisation fails the
   moment SOL is included.
3. **Magnitude is never stable**, even for the surviving effect — so the *strength* of any funding
   relationship cannot be relied upon period-to-period.
4. Combined with correlation ≈ 0 (predictive file), the time-series evidence says funding's
   informational content is **narrow and fragile**, not broad and repeatable.

Caveats from the predictive file carry over in full: 3-symbol predictive scope, overlapping-window
autocorrelation (which *inflates* apparent fold stability — so the real bar is higher than these signs
suggest), and no cost/profitability assessment.
