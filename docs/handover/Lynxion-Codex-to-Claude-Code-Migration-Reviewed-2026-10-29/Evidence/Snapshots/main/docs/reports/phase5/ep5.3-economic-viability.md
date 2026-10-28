# E-P5.3 — Economic Viability After Execution Fixes

_8355 trades, 90d × {BTC,ETH,SOL} × 12 strategies, frozen POST baseline (B1/B2 fixed). pnl is NET (fees 0.1%/side + slippage). **Execution-corrected** = GROSS R (pre-cost, edge of signal+geometry with correct fills); **Economic** = NET R (post-cost reality). Realistic conditions._

## Ranked by TRUE post-cost expectancy (net R/trade)

| rank | strategy | trades | **net exp R** | gross exp R | cost drag R | win% | payoff (W/L) | TP net R | SL net R | reward leg | label |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | liquidity | 368 | **-0.836** | -0.246 | 0.589 | 27% | 0.28 | +0.03 | -1.59 | 0.64R | Non-Viable |
| 2 | mean_reversion | 199 | **-0.865** | -0.320 | 0.546 | 28% | 0.27 | +0.10 | -1.54 | 0.67R | Non-Viable |
| 3 | trend_following | 239 | **-0.931** | -0.339 | 0.592 | 23% | 0.21 | -0.04 | -1.58 | 0.60R | Non-Viable |
| 4 | oi_footprint | 474 | **-0.949** | -0.348 | 0.602 | 23% | 0.25 | -0.03 | -1.60 | 0.62R | Non-Viable |
| 5 | momentum | 95 | **-0.977** | -0.430 | 0.547 | 18% | 0.32 | +0.08 | -1.54 | 0.66R | Non-Viable |
| 6 | vwap_reversal | 954 | **-1.041** | -0.364 | 0.677 | 18% | 0.23 | -0.20 | -1.68 | 0.51R | Non-Viable |
| 7 | crypto_breakout | 1139 | **-1.077** | -0.405 | 0.673 | 15% | 0.24 | -0.25 | -1.66 | 0.51R | Non-Viable |
| 8 | mtf_trend | 2040 | **-1.137** | -0.448 | 0.689 | 12% | 0.23 | -0.33 | -1.67 | 0.48R | Non-Viable |
| 9 | breakout | 1281 | **-1.161** | -0.468 | 0.693 | 13% | 0.24 | -0.28 | -1.69 | 0.49R | Non-Viable |
| 10 | scalping | 1425 | **-1.175** | -0.438 | 0.737 | 12% | 0.26 | -0.43 | -1.72 | 0.48R | Non-Viable |
| 11 | volatility_breakout | 141 | **-1.400** | -0.718 | 0.682 | 2% | 0.11 | -0.38 | -1.66 | 0.48R | Non-Viable |

## Execution-corrected vs Economic (the cost cliff)

For each strategy: does correct-execution edge exist pre-cost, and does it survive fees+slippage?

| strategy | gross exp R (corrected) | net exp R (economic) | survives costs? |
|---|---:|---:|---|
| liquidity | -0.246 | -0.836 | NO (negative even pre-cost) |
| mean_reversion | -0.320 | -0.865 | NO (negative even pre-cost) |
| trend_following | -0.339 | -0.931 | NO (negative even pre-cost) |
| oi_footprint | -0.348 | -0.949 | NO (negative even pre-cost) |
| momentum | -0.430 | -0.977 | NO (negative even pre-cost) |
| vwap_reversal | -0.364 | -1.041 | NO (negative even pre-cost) |
| crypto_breakout | -0.405 | -1.077 | NO (negative even pre-cost) |
| mtf_trend | -0.448 | -1.137 | NO (negative even pre-cost) |
| breakout | -0.468 | -1.161 | NO (negative even pre-cost) |
| scalping | -0.438 | -1.175 | NO (negative even pre-cost) |
| volatility_breakout | -0.718 | -1.400 | NO (negative even pre-cost) |

## Primary loss driver (per strategy, quantified)

| strategy | net exp R | primary driver |
|---|---:|---|
| liquidity | -0.836 | TP/SL geometry: reward leg 0.64R < 1R risk (R:R<1); payoff 0.28, so 27% win-rate can't cover losers |
| mean_reversion | -0.865 | TP/SL geometry: reward leg 0.67R < 1R risk (R:R<1); payoff 0.27, so 28% win-rate can't cover losers |
| trend_following | -0.931 | TP/SL geometry: reward leg 0.60R < 1R risk (R:R<1); payoff 0.21, so 23% win-rate can't cover losers |
| oi_footprint | -0.949 | TP/SL geometry: reward leg 0.62R < 1R risk (R:R<1); payoff 0.25, so 23% win-rate can't cover losers |
| momentum | -0.977 | TP/SL geometry: reward leg 0.66R < 1R risk (R:R<1); payoff 0.32, so 18% win-rate can't cover losers |
| vwap_reversal | -1.041 | TP/SL geometry: reward leg 0.51R < 1R risk (R:R<1); payoff 0.23, so 18% win-rate can't cover losers |
| crypto_breakout | -1.077 | TP/SL geometry: reward leg 0.51R < 1R risk (R:R<1); payoff 0.24, so 15% win-rate can't cover losers |
| mtf_trend | -1.137 | TP/SL geometry: reward leg 0.48R < 1R risk (R:R<1); payoff 0.23, so 12% win-rate can't cover losers |
| breakout | -1.161 | TP/SL geometry: reward leg 0.49R < 1R risk (R:R<1); payoff 0.24, so 13% win-rate can't cover losers |
| scalping | -1.175 | TP/SL geometry: reward leg 0.48R < 1R risk (R:R<1); payoff 0.26, so 12% win-rate can't cover losers |
| volatility_breakout | -1.400 | TP/SL geometry: reward leg 0.48R < 1R risk (R:R<1); payoff 0.11, so 2% win-rate can't cover losers |

**Loss-driver tally:** {'TP/SL geometry': 11}

## Verdict — Are ANY strategies economically viable under realistic conditions?

**NO. Zero strategies have positive post-cost expectancy.** Not one of the 12 strategies clears breakeven after fees+slippage on any tested cell.

**Closest to breakeven:** liquidity (-0.836R), mean_reversion (-0.865R), trend_following (-0.931R).

**Borderline (gross-positive or within −0.10R, structurally adjustable): 0** — none.

_Classification: Economically Viable (net>0) · Borderline (gross>0 or net>−0.10R) · Non-Viable (negative even pre-cost). No optimization, no strategy-logic changes, no new epics — diagnosis only._

---

## Critical interpretation (analyst, post-run)

The headline is not just "unprofitable after costs" — it is **unprofitable even
before costs.** Every one of the 11 evaluable strategies has **negative GROSS
expectancy** (−0.25R to −0.72R) on the execution-corrected, bug-free path. This
is the single most important economic finding of E-P5.3: with *perfect, free*
execution the strategies still lose. Costs deepen the hole; they did not dig it.

Three layered, quantified drivers (all present in every strategy):

1. **No directional edge in the entries (primary).** Gross expectancy is negative
   across the board → the entry signals do not predict forward direction well
   enough to win even before paying anything. Trade-management overlays cannot
   create edge that isn't there.
2. **Adverse R:R geometry — B7 (structural).** Mean reward leg **0.51R vs 1R
   risk** (TP set at ~half the stop distance); payoff ratio 0.11–0.32. At the
   realised 12–28% win rates this can never break even. Confirmed.
3. **Stops too tight relative to transaction costs (cost cliff).** Cost drag
   averages **~0.6R/trade**; SL exits realise **−1.67R** (not the intended −1R)
   and 62% of *TP* hits still net a loss. This only happens when the risk unit
   |entry−stop| is comparable to round-trip fees+slippage — i.e. stops are so
   tight that fixed costs consume a large fraction of R. High-frequency strategies
   (scalping, mtf_trend, breakout: 1.3k–2.0k trades) carry the worst drag
   (0.69–0.74R) → **overtrading amplifies the cost cliff.**

**Caveat on the lifecycle "opportunity" figures** (in the companion
`ep5.3-lifecycle-forensics-report.md`): the breakeven/trailing/partial upside —
especially the trailing "+1.27R/trade" — is a mechanical **upper bound, not an
achievable gain.** It is computed against the cost-inflated realised R (−1.67R on
stops), assumes a fraction of transient MFE is captured as a real exit, and
ignores the costs that exit would itself pay. **B8 (missing breakeven/trailing/
partial) is real but secondary: it cannot rescue strategies that are negative
*gross*.** The binding constraints are entry edge (driver 1) and SL/TP geometry +
cost structure (drivers 2–3) — in that order.

**Bottom line:** under realistic conditions, **no strategy is economically
viable, and none is close** (best −0.836R, none gross-positive, none Borderline).
This is a stronger result than the matrix alone: the deficit is in the trading
hypotheses' realised entry edge and risk geometry, not merely in execution or
cost tuning.
