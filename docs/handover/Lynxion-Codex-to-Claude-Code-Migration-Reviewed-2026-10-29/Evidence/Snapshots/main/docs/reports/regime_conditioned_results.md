# Regime-Conditioned Results (Phase B)

**Date:** 2026-06-13. Companion to `strategy_deployment_validation.md`. Per-bar regime labeled by a
transparent, lookahead-safe classifier (sma20/sma50 trend + ATR-expansion for breakout). "In-regime"
expectancy counts only signals fired in the strategy's intended regime, net of 0.30% round-trip cost,
at the design-TF holding horizon. (BTC shown for coverage; full per-symbol in `per_symbol_strategy_results.md`.)

## 1. Regime coverage — what fraction of signals fire in the intended regime? (BTC)

| Strategy | Intended regime | Total sigs | In-regime | In-regime % | Signal regime mix |
|---|---|---|---|---|---|
| trend_following | trending | 747 | 582 | **78%** | trend 582 / breakout 92 / range 72 |
| mtf_trend | trending | 15,935 | 9,945 | 62% | trend 9945 / range 3020 / breakout 2970 |
| momentum | trending | 1,334 | 702 | 53% | trend 702 / **range 473** / breakout 159 |
| breakout | breakout | 210 | 80 | 38% | breakout 80 / trend 121 / range 9 |
| volatility_breakout | breakout | 288 | 74 | 26% | breakout 74 / trend 157 / range 57 |
| liquidity | ranging | 139 | 34 | 24% | range 34 / trend 78 / breakout 27 |
| vwap_reversal | ranging | 43 | 5 | 12% | range 5 / trend 23 / breakout 15 |
| sweep_scalper | breakout | 1,545 | 128 | **8%** | breakout 128 / range 632 / trend 769 |
| mean_reversion | ranging | 1 | 0 | n/a | the 1 signal fired in a trending bar |
| oi_footprint | (mixed/none) | 1,132 | n/a | n/a | no single intended regime (volume proxy) |

**Finding 1 — misdeployment confirmed:** most strategies fire the *majority* of their signals
**outside** their intended regime (sweep_scalper 8% in-regime, vwap_reversal 12%, liquidity 24%,
volatility_breakout 26%, breakout 38%, momentum 53%). The system never gated activation by regime, so
each strategy spent most of its trades in regimes it explicitly should avoid. This validates Phase B's
premise.

## 2. In-regime expectancy — does conditioning on the right regime reveal an edge? (% net per trade)

| Strategy | BTC in-reg | ETH in-reg | SOL in-reg | In-regime sample | Cross-period stable? |
|---|---|---|---|---|---|
| trend_following | −0.21 | −0.29 | −0.16 | 582 / 635 / 714 | BTC/ETH yes(neg); SOL flip |
| momentum | −0.29 | −0.26 | −0.35 | 702 / 1157 / 1331 | **all stable-negative** |
| mtf_trend | −0.31 | −0.28 | −0.31 | 9945 / 10112 / 11037 | **all stable-negative** |
| sweep_scalper | −0.33 | −0.27 | −0.21 | 128 / 1213 / 40 | stable-negative |
| breakout | −0.45 | −0.16 | −0.37 | 80 / 105 / 91 | BTC neg; ETH/SOL flip |
| liquidity | −0.28 | −0.30 | −0.36 | 34 / 42 / 51 | BTC/SOL neg; ETH flip |
| volatility_breakout | −0.22 | **+0.13** | **+0.34** | 74 / 64 / 38 | ETH/SOL **FLIP** (first-half only) |
| mean_reversion | — | — | — | 0 / 0 / 0 | unjudgeable |
| vwap_reversal | −0.34 | −0.07 | +0.13 | 5 / 4 / 7 | unjudgeable (n<10) |
| oi_footprint | — | — | — | 0 / 0 / 0 | n/a (no regime gate) |

**Finding 2 — regime conditioning does NOT reveal an edge.** Even restricted to the intended regime:
- trend_following, momentum, mtf_trend, sweep_scalper: **negative and cross-period stable** (the
  directional signal is anti-predictive in its own regime net of cost; win rates ~30%).
- breakout, liquidity: negative where sample is adequate; otherwise unstable.
- volatility_breakout: the only positive in-regime cells (ETH +0.13%, SOL +0.34%) are **entirely
  first-half** and reverse to large negatives in the second half (ETH +0.64→−0.32, SOL +1.35→−0.66) →
  **not stable** → period-specific noise, not an edge.
- mean_reversion (0 in-regime) and vwap_reversal (4–7 in-regime): **too selective to judge** even on
  their design TF.

**Conclusion:** Regime conditioning improved fairness but not outcomes. No strategy shows a positive,
cross-period-stable in-regime edge on any symbol. Regime-based activation is still operationally
worth implementing (it would stop trading the ~⅓–¾ of signals fired in the wrong regime), but it does
**not** convert any of these strategies to READY.
