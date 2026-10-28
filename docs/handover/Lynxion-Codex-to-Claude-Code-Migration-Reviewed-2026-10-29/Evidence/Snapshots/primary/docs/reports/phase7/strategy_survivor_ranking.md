# Phase 7 — Strategy Survivor Ranking

**Date:** 2026-06-12. Strategies ranked by **evidence of viability** (proximity to a
defensible READY), combining: trade sample, positive-cell count, GO verdicts, aggregate
PnL, and — decisively — **walk-forward out-of-sample persistence** (positive segments out
of 4 disjoint quarters, per symbol). No strategy is profitable+stable; this ranks
"least-far" vs "dead".

Ranking key: WFO persistence is weighted highest (it is the only test that rejects
in-sample artifacts). "best WFO" = max positive-segments/traded-segments on any symbol.

| rank | strategy | trades | pos cells | GO | Σ PnL | best WFO (sym) | tier |
|---|---|---|---|---|---|---|---|
| 1 | oi_footprint | 3204 | 3 | 1 | −11054 | 2/4 (ETH) | Tier 1 — least far (data-gated) |
| 2 | momentum | 2487 | 4 | 1 | −17456 | 2/4 (BTC, ETH) | Tier 1 |
| 3 | trend_following | 2106 | 2 | 2 | −7594 | 2/4 (BTC, ETH) | Tier 1 |
| 4 | mtf_trend | 5107 | 2 | 1 | −19798 | 1/4 (BTC, ETH) | Tier 2 |
| 5 | liquidity | 474 | 5 | 0 | −2472 | 1/1 (ETH, tiny) | Tier 2 |
| 6 | sweep_scalper | 225 | 7 | 0 | −810 | ≤1/1 | Tier 3 — too little data |
| 7 | volatility_breakout | 236 | 6 | 0 | −592 | 0 | Tier 3 |
| 8 | vwap_reversal | 12 | 5 | 0 | −72 | 0/0 | Tier 3 — barely trades |
| 9 | mean_reversion | 6 | 3 | 0 | +25 | 0/0 | Tier 3 — barely trades |
| 10 | breakout | 0 | 0 | 0 | 0 | — | Tier 4 — untradeable (B1 gate) |
| 11 | crypto_breakout | 0 | 0 | 0 | 0 | — | Tier 4 — redundant alias |
| 12 | scalping | 2025 | 6 | 2 | −8317 | 2/4 (ETH) but neg every TF/sym aggregate | Tier 4 — cost-structural dead end |

## Reading the ranking
- **No survivor clears the viability bar.** Even Tier-1 maxes at **2/4 WFO segments (a
  coin-flip)** and is negative in aggregate. Tier-1 = "closest, given a *non-tuning* lever"
  (real-OI data for oi_footprint; cross-symbol/WFO gating for momentum/trend_following).
- **Tier 3** is sample-starved (vwap_reversal, mean_reversion barely trade; sweep_scalper
  thin) — they cannot be judged viable or rehabilitated without changing their selectivity
  (forbidden).
- **Tier 4** are dead ends: breakout (cannot trade as wired — B1), crypto_breakout
  (redundant alias), scalping (structural cost incompatibility, loses everywhere).

## Honest note
Aggregate PnL does **not** reorder the verdict: a higher trade count with larger losses
(mtf_trend −19.8k, momentum −17.5k) is *worse*, not better. The ranking is by *proximity
to defensible edge*, and the WFO column shows even the top of the list has none that
persists. There is no statistically-supported survivor.
