# Phase 14 — Funding Predictive Analysis

**Date:** 2026-06-13. Analysis only. **No trading signals, no strategy, no cost model, no profitability
estimate.** This file measures *predictive relationships only* (Tasks 3–4): does the funding regime at
time *t* carry information about the **forward price return** over the next 4h / 12h / 24h / 72h, and is
that information present **beyond OHLCV**?

## Method (what was measured, and what was not)

- **Symbols:** BTC, ETH, SOL — the symbols with funding *and* full 3-year aligned 1h price (other 21
  symbols lack matching 3y intraday price on disk; see audit). Each: **3,274–3,275 aligned funding
  observations** over 2023-06-13 → 2026-06-11.
- **Forward return** at horizon *h* = (close[t+h] − close[t]) / close[t]. Pure price change. **No fees,
  no slippage, no position, no signal** — this is information content, not a backtest.
- **Funding regimes** (per symbol, from its own funding distribution):
  - `extreme_pos` = funding ≥ p90 (soft "elevated" bucket — see profile tie-note)
  - `extreme_neg` = funding ≤ p10 (clean 10% tail)
  - `expansion` = funding rose vs previous interval
  - `contraction` = funding fell vs previous interval
  - `transition` = funding sign flipped vs previous interval
- **Metrics:** (1) Pearson + Spearman-IC of funding vs forward return; (2) conditional mean forward
  return per regime, reported as **excess vs the unconditional baseline** (because the 3-year drift is
  non-zero, raw conditional means must be read against baseline). Walk-forward stability →
  `funding_walkforward_validation.md`.
- Regime thresholds are **descriptive percentiles of funding**, not tuned strategy parameters. No
  threshold was optimised against returns.

## Result 1 — Linear correlation funding ↔ forward return ≈ 0 over 3 years

| | 4h | 12h | 24h | 72h |
|---|---|---|---|---|
| BTC pearson / IC | −0.009 / +0.005 | −0.021 / −0.001 | +0.003 / −0.009 | **+0.018 / −0.027** |
| ETH pearson / IC | −0.015 / +0.005 | −0.024 / −0.008 | −0.017 / −0.012 | −0.011 / −0.004 |
| SOL pearson / IC | −0.002 / +0.009 | +0.011 / +0.021 | +0.027 / +0.027 | +0.040 / +0.032 |

- **No usable linear/rank relationship.** All |IC| ≤ 0.032 over 3 years.
- **Important correction of a window artifact:** on the *1-year* price overlap (2025-06→2026-06) BTC
  showed IC = **−0.140 @72h** (an apparent "high funding → lower return" contrarian effect). Extending
  price to the **full 3 years collapses it to −0.027** — it was a property of the 2025-26 drawdown, not
  a stable relationship. This is the single most important reason the analysis was run over 3 years, not
  1. **A 1-year funding study here would have produced a false positive.**

## Result 2 — Conditional forward return by regime (excess vs baseline, %)

| Regime | BTC 24h / 72h | ETH 24h / 72h | SOL 24h / 72h |
|---|---|---|---|
| **extreme_neg** | **+0.25 / +0.39** | **+0.38 / +0.68** | −0.17 / −0.33 |
| extreme_pos | −0.00 / +0.07 | +0.08 / +0.24 | +0.17 / +0.59 |
| expansion | +0.03 / +0.19 | −0.03 / −0.14 | −0.02 / −0.20 |
| contraction | −0.00 / −0.14 | −0.03 / −0.02 | −0.08 / −0.07 |
| transition | +0.01 / +0.05 | −0.16 / −0.34 | −0.14 / −0.12 |

**Readings:**
- **The only directionally meaningful, theory-aligned effect is `extreme_neg` → *positive* forward
  return at 24h/72h on BTC and ETH** (+0.25% to +0.68% above baseline). Interpretation: deeply negative
  funding = shorts crowded / longs paid → mean-reverting bounce. **SOL does not share it** (−0.17/−0.33).
- **The textbook "crowded longs reverse" hypothesis is NOT supported.** `extreme_pos` shows *no*
  negative forward return on any symbol over 3 years (BTC ≈0, ETH/SOL mildly positive). Whatever the
  1-year window suggested, it does not survive.
- `expansion`/`contraction`/`transition` are small and **sign-inconsistent across the three symbols** →
  no coherent cross-symbol information.

## Result 3 — Is there information *beyond OHLCV*?

Funding is **exogenous to OHLCV by construction** (it is a derivatives-market positioning-cost series,
not a transform of spot price/volume). So any *stable, repeatable* conditional effect would, by
definition, be information beyond OHLCV. The evidence:

- **Correlation:** ~0 over 3 years → no *linear* information beyond OHLCV.
- **Conditional expectancy:** one regime (`extreme_neg`, 24–72h) carries a real conditional shift on
  BTC/ETH — this *is* a candidate "beyond-OHLCV" signal, because nothing in spot OHLCV directly encodes
  perp funding. But it is single-regime, two-of-three-symbols, and modest.
- **Stability through time:** see `funding_walkforward_validation.md` — `extreme_neg` (BTC/ETH) is the
  *only* effect that holds its sign across all 4 walk-forward folds; everything else is fold-unstable.
- **Cross-symbol consistency:** **poor.** SOL contradicts the BTC/ETH `extreme_neg` bounce; the
  `extreme_pos` sign disagrees across symbols. A genuine, structural funding effect should generalise
  across the three majors — it does not.

## Honest caveats (these bound every number above)

1. **Predictive scope = BTC/ETH/SOL only.** The other 21 funding symbols could not be tested for lack of
   3-year intraday price. Cross-symbol "consistency" is therefore judged on 3 names, not 24.
2. **Overlapping windows.** Observations are 8h-spaced but horizons run to 72h, so successive forward
   returns overlap heavily → strong autocorrelation in the sample → the *effective* sample size is far
   below the nominal ~3,275, inflating apparent stability. The walk-forward partially controls this; t-
   stats would be optimistic if computed naively (not reported, to avoid a false-precision claim).
3. **No cost, no profitability — by mandate.** The `extreme_neg` excess (~+0.25–0.68% over 24–72h) is an
   *information* measurement, **not** a tradable return; whether it survives the ~0.30% round-trip cost
   used in prior phases is explicitly **out of scope** here and **not asserted**.
4. **`extreme_pos` is a soft bucket** for several symbols (funding ties at the venue default inflate
   `≥p90`); the clean tail is `extreme_neg`, which is also where the only signal sits.

## Section verdict

Funding shows **no broad predictive information** about forward price returns over 3 years (correlation
≈ 0; four of five regimes inconsistent across symbols). There is **one narrow, theory-aligned thread** —
**extreme-negative funding → mild positive 24–72h forward return on BTC and ETH** — which is the only
relationship that even resembles information beyond OHLCV. Its repeatability is tested next.
