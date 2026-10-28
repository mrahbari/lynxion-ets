# E-P5.5 — Microstructure & Adaptation Forensics (diagnosis only)

_8355 trades (all LONGS), 90d × {BTC,ETH,SOL} × 12 strategies, frozen POST baseline. Execution cost = gross_R − net_R (EMPIRICAL total: fees + spread + slippage + impact; per-component split not recoverable from the dump). No engine/strategy/architecture changes — quantification only._

## Q1 — Profitability lost to spread / slippage / liquidity

- **Total execution cost: 0.677R/trade** (~**10.0 bps** of notional).
- Mean **stop width: 16.9 bps** of price.
- This converts gross expectancy **-0.418R** into net **-1.094R** — i.e. execution costs are the mechanical bridge between the (already negative) signal edge and the realised result.

**Root cause — the cost cliff is geometric, not exotic.** The realised cost is only ~10 bps of notional (a normal cost stack: fee 0.1%/side, spread 2bps, slippage 0.0005, impact). It becomes catastrophic ONLY because stops average ~17 bps wide: a 10-bps cost on a 17-bps stop = ~0.68R consumed per trade. Spread/slippage/liquidity are not mispriced — the **stops are simply far too tight relative to costs** (ties to B7). Halving trade frequency or widening stops to dwarf the bps cost would remove most of this drag.

## Q2 — Which strategies are most microstructure-sensitive?

Ranked by execution cost (R/trade). Sensitivity = cost-in-R, which rises as stops tighten. 'micro-dep?' = named edge relies on OHLCV-only proxy/stub features (B12).

| strategy | trades | stop bps | **cost R/trade** | cost bps | gross expR | net expR | micro-dep? |
|---|---:|---:|---:|---:|---:|---:|:--:|
| scalping | 1425 | 16 | **0.737** | 10 | -0.438 | -1.175 | — |
| breakout | 1281 | 16 | **0.693** | 10 | -0.468 | -1.161 | — |
| mtf_trend | 2040 | 16 | **0.689** | 10 | -0.448 | -1.137 | — |
| volatility_breakout | 141 | 15 | **0.682** | 10 | -0.718 | -1.400 | — |
| vwap_reversal | 954 | 17 | **0.677** | 10 | -0.364 | -1.041 | YES |
| crypto_breakout | 1139 | 17 | **0.673** | 10 | -0.405 | -1.077 | — |
| oi_footprint | 474 | 19 | **0.602** | 10 | -0.348 | -0.949 | YES |
| trend_following | 239 | 19 | **0.592** | 10 | -0.339 | -0.931 | — |
| liquidity | 368 | 20 | **0.589** | 10 | -0.246 | -0.836 | YES |
| momentum | 95 | 20 | **0.547** | 10 | -0.430 | -0.977 | — |
| mean_reversion | 199 | 21 | **0.546** | 10 | -0.320 | -0.865 | — |

- **Most cost-sensitive:** scalping (0.737R/trade, stop 16bps). **Least:** mean_reversion (0.546R/trade, stop 21bps).
- Sensitivity tracks **stop tightness / trade frequency**: tighter stops and higher turnover → larger fixed-cost bite per R. Scalping/breakout-type strategies are structurally the most microstructure-exposed.

## B12 — microstructure-named strategies on OHLCV-only data

4 strategies are named for microstructure edges (sweep/absorption/imbalance/OI) but run on OHLCV-only proxies/stubs (`detect_sweep`→0, OI `*1.5`): **liquidity, oi_footprint, sweep_scalper, vwap_reversal**. Net expectancy (vwap_reversal -1.041R, oi_footprint -0.949R, liquidity -0.836R) cannot reflect their intended edge — they trade on degraded signals. This is INSUFFICIENT-EVIDENCE for those hypotheses, not disproof (needs L2/trades/OI/funding data to test properly).

## B13 — adaptation / learning loop

`recalibrate_classifier()` is a print stub; adaptive weights not confirmed to persist. No within-run regime adaptation is observable: expectancy is uniformly negative across entry regimes (−1.0 to −1.2R; E-P5.4) with no sign of the system adapting sizing/selection. Adaptation cannot be validated and is moot while gross edge is absent (B14).

## E-P5.5 findings (6-part)

1. **Findings:** execution costs ~0.68R/trade (~10 bps) on stops only ~17bps wide; cost-sensitivity ranks with stop tightness/frequency; 4 micro-named strategies run on proxy/stub features (B12); adaptation stubbed (B13).
2. **Root causes:** stops far too tight vs a normal bps cost stack (B7-linked); B12 OHLCV-only microstructure proxies; B13 learning loop a stub.
3. **Profitability impact:** total execution cost ~0.68R/trade is the mechanical bridge from gross -0.42R to net -1.09R — the largest single mechanical drag, but a SYMPTOM of tight stops, not mispriced microstructure.
4. **Recommended fixes (NOT executed — diagnosis only):** widen stops to dwarf costs / reduce turnover / cost-aware entry gate (B7); acquire L2/trades/OI/funding to test micro strategies (B12); implement real adaptation (B13). Deferred to remediation mode.
5. **Estimated upside:** right-sizing stops + lower turnover removes most of the ~0.68R/trade drag (large loss-REDUCTION), but gross is still -0.42R (negative, B14) → does not reach profit alone.
6. **Priority ranking (cumulative):** B14 (entry edge) ≫ B7 (R:R + tight stops vs cost — drives the E-P5.5 cost cliff) > B10 (portfolio risk) > B8 (lifecycle) > B9 (MTF, no benefit) > B12 (needs data) > B13 (moot until edge exists).
