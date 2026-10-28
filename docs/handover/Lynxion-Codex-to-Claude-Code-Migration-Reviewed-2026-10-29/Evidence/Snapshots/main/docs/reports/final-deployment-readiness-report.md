# Final Deployment Readiness Report

**Date:** 2026-06-12. **Scope:** the 12 fixed production strategies, re-architected onto
resampled higher timeframes (1m canonical data → 15m/30m/1h decision TFs), evaluated on
BTC/ETH/SOL with **existing production parameters only** (no tuning).

> **VERDICT: NOT DEPLOYABLE. Do not allocate live capital to any strategy.**
> **READY 0 · NEEDS_IMPROVEMENT 11 · NON_VIABLE 1.**

_(Evidence base: complete 15m/30m/1h matrices [324 cells] + walk-forward OOS validation
[144 cells, 4 disjoint segments]. Conclusion is statistically decisive and is now
reinforced by out-of-sample testing — see `walk-forward-validation-report.md`.)_

> **Out-of-sample confirmation (strongest evidence):** a walk-forward test over 4 disjoint
> ~3-month segments at 1h found **zero temporally-stable (strategy, symbol) pairs** — no
> strategy is positive in ≥3 of 4 OOS segments on any symbol (best = 2/4, a coin-flip).
> Even oi_footprint ETH (the best nested-window cell, +165 GO) is positive in only 2 of 4
> disjoint quarters. **The positive cells are in-sample artifacts; there is no persistent
> edge.** This removes any "close candidate" caveat.

## The decision in one line
After moving every strategy off 1m (which is structurally cost-incompatible) onto its
intended higher decision timeframes, **no strategy is profitable in a way that is stable
across BTC, ETH and SOL** — so none meets the READY bar (profitable + stable across
symbols + stable across horizons + statistically supported).

## Cross-symbol × cross-horizon evidence (Σ PnL per symbol, $ on 10k capital)

| strategy | 15m BTC / ETH / SOL | 1h BTC / ETH / SOL | GO cells | trades |
|---|---|---|---|---|
| trend_following | −1388 / −1187 / −1341 | −214 / −295 / −481 | 2 | 1436 |
| momentum | −633 / −1244 / −4160 | +41 / −827 / −3364 | 1 | 1628 |
| mtf_trend | −2054 / −2467 / −4017 | +9 / −1316 / −2983 | 1 | 3579 |
| oi_footprint | −2083 / −2438 / −2889 | −634 / **+405** / −965 | 1 | 2284 |
| liquidity | −43 / +58 / −505 | −626 / +58 / −492 | 0 | 303 |
| volatility_breakout | −232 / −2 / −73 | −119 / −18 / −219 | 0 | 172 |
| sweep_scalper | +5 / −1 / −12 | −24 / −156 / +34 | 0 | 116 |
| scalping | −780 / −164 / −769 | −956 / −1919 / −1817 | 1 | 1356 |
| vwap_reversal | −37 / −81 / +1 | 0 / 0 / 0 | 0 | 7 |
| mean_reversion | 0 / 0 / −39 | 0 / 0 / 0 | 0 | 2 |
| breakout / crypto_breakout | 0 / 0 / 0 | 0 / 0 / 0 | 0 | 0 |

**Not a single strategy is positive on all three symbols at any horizon.** The best
single cells (oi_footprint ETH 1h +405; momentum/mtf_trend BTC 1h marginally +) are
contradicted by catastrophic losses on the other symbols (notably SOL).

## Two confirmed structural facts
1. **1m is cost-incompatible** (TP=2.25×ATR≈0.10% ≪ 0.30% round-trip cost; breakeven ≈15m)
   — established in rehabilitation, the reason this re-architecture was required.
2. **15m sits ON the cost cliff and is *worse* than 1h.** Aggregate 15m PnL is more
   negative than 1h for nearly every strategy, because at 15m TP (≈0.57%) only narrowly
   clears the 0.30% cost, leaving little margin. The mandated role of 15m as "primary
   signal timeframe" is the least cost-robust of the viable TFs; **1h is the most
   cost-robust horizon tested**, yet still shows no stable edge.

## Why none is READY (10-point check, all fail on profitability/stability)
Implementation (dims 1–8), data sufficiency at higher TF, and timeframe placement are now
largely satisfied — but **profitability and cross-symbol/cross-horizon stability are not**.
Per the READY rule, a correctly-implemented strategy without stable positive expectancy is
**NEEDS_IMPROVEMENT**, and one with structural incompatibility is **NON_VIABLE**.

## Final classification
- **NON_VIABLE (1):** `scalping` — negative on every symbol AND every timeframe (1m/15m/1h);
  structurally cost-sensitive.
- **NEEDS_IMPROVEMENT (11):** all others — correct and measurable, but no stable profitable
  edge. `oi_footprint`, `momentum`, `mtf_trend` are the *closest* (isolated positive cells)
  but fail cross-symbol stability; `breakout`/`crypto_breakout` are blocked by a documented
  Type-B confidence gate; `vwap_reversal`/`mean_reversion` barely trade at higher TF.
- **READY (0).**

## Deployment recommendation
**Deploy nothing.** Prerequisites before reconsideration (none is tuning):
1. A strategy must be **positive across BTC/ETH/SOL and across ≥2 horizons** before any
   READY claim — single-cell positives are noise.
2. **1h is the most cost-robust horizon**; prefer it over 15m for any future viability work.
3. **Walk-forward / out-of-sample** validation required before live capital.
4. Resolve **oi_footprint's** real-OI data dependency before trusting its ETH positive.
5. Do **not** pursue profitability via Type-B threshold changes (curve-fitting).

The re-architecture achieved its engineering goal (strategies now decide on cost-viable
timeframes), but the trading conclusion is unchanged from rehabilitation: **the existing
suite has no demonstrable, stable edge and is not production-ready.**
