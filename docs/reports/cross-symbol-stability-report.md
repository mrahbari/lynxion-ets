# Cross-Symbol Stability Report

**Date:** 2026-06-12. Tests whether any production strategy behaves **consistently across
BTC, ETH and SOL** on the cost-viable timeframes (15m/30m/1h) — a precondition for READY.
Existing params only. Evidence: 15m (108) + 1h (108) complete; 30m completing
(confirmatory). Cells counted only when statistically meaningful (≥30 closed trades).

## Core result: zero cross-symbol stability

**Positive significant cells per symbol (pos / total, across all TF×window combinations):**

| strategy | BTC | ETH | SOL | all-positive on any symbol? |
|---|---|---|---|---|
| mtf_trend | 2/7 | 0/6 | 0/7 | no |
| oi_footprint | 0/6 | 2/6 | 0/6 | no |
| momentum | 1/4 | 0/5 | 0/7 | no |
| trend_following | 0/5 | 1/5 | 0/5 | no |
| scalping | 0/5 | 1/4 | 0/5 | no |
| liquidity | 0/0 | 0/1 | 0/1 | no |
| volatility_breakout | 0/1 | 0/0 | 0/0 | no |
| sweep_scalper / vwap_reversal / mean_reversion / breakout / crypto_breakout | (too few significant cells) | | | no |

**No strategy is consistently positive on even a single symbol**, let alone all three.
The best any strategy manages is a minority of positive cells on its *best* symbol
(mtf_trend 2/7 on BTC; oi_footprint 2/6 on ETH) — and 0 on the other two.

## SOL is a universal failure mode
**Across every strategy, SOL produced 0 positive significant cells.** Strategies that
show isolated positives on BTC or ETH are uniformly negative — often catastrophically —
on SOL (e.g. momentum SOL −3364 @1h, mtf_trend SOL −2983 @1h, oi_footprint SOL −965 @1h).
Any apparent edge is **symbol-specific and does not generalize** — the signature of noise
/ overfit-to-one-market rather than a robust effect.

## Symbol-specificity of the rare positives
- **BTC-favourable:** mtf_trend, momentum (marginal positives, 1h).
- **ETH-favourable:** oi_footprint (best, +405), trend_following, scalping (isolated).
- **SOL-favourable:** none.

A genuine edge would appear on all three liquid majors. The disjoint, non-overlapping
pattern (different strategies "work" on different single symbols, none on SOL) indicates
the positives are not a stable, transferable signal.

## Horizon note (cross-horizon stability)
15m is systematically **worse** than 1h (it sits on the ~15m cost-breakeven cliff), and
30m (completing) tracks between them. No strategy flips from negative to stably-positive
as the horizon changes; the horizon axis does not rescue any strategy either.

## Conclusion
**Cross-symbol stability: FAIL for all 12 strategies.** This is an independent,
sufficient reason (beyond aggregate unprofitability) that **no strategy qualifies as
READY**. Future viability work must gate on *cross-symbol* (and cross-horizon) positive
expectancy — a bar none of the current suite clears.
