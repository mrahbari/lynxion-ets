# Phase 18 — Cross-Asset Lead-Lag Analysis (T1)

**Date:** 2026-06-13. Analysis only; no strategy/parameter/threshold/risk/execution changes; no
profitability claim. Test T1: does **BTC lead ETH / SOL** at 1-minute resolution (Binance futures, ~90
days, 129,600 bars)? Cost-free lead-lag information + cost-adjusted (0.30% round-trip) deployability +
4-fold walk-forward.

## Lead-lag cross-correlation `corr(leader_ret[t−k], follower_ret[t])`

| Pair | k=0 (contemporaneous) | k=1 (1-min lead) | k=2 | k=3 |
|---|---:|---:|---:|---:|
| BTC → ETH | **0.878** | +0.0097 | −0.012 | −0.007 |
| ETH → BTC | 0.878 | +0.0221 | −0.024 | −0.012 |
| BTC → SOL | **0.834** | +0.0188 | −0.018 | −0.011 |
| SOL → BTC | 0.834 | +0.0160 | −0.024 | −0.007 |

**Reading.**
- **Contemporaneous co-movement is high** (0.83–0.88): BTC and the alts move together *within the same
  minute*. This is the expected, well-known co-movement — and it is **OHLCV-visible**, not new information.
- **The lead component (k=1) is tiny** (~0.01–0.02) and, crucially, **not directionally clean**: the
  reverse direction (alt→BTC) is comparable to or larger than BTC→alt (e.g. ETH→BTC 0.022 > BTC→ETH 0.010).
  So there is **no robust "BTC leads alts" lead at 1-minute** — the residual is near-noise and ambiguous
  in direction.
- At k≥2 the correlation goes mildly negative (1-bar mean-reversion of the co-move), again tiny.

## Cost-adjusted deployability (trade the alt in BTC's prior-bar direction)

| Signal | gross/bar | net (−0.30%) | win | WFO folds+ |
|---|---:|---:|---:|:--:|
| BTC → ETH | +0.0000079 | −0.2992% | 0.484 | 0/4 |
| BTC → SOL | +0.0000093 | −0.2991% | 0.446 | 0/4 |

- **Gross expectancy ≈ 0** (≈ +0.000008/bar) — the BTC-lead signal has essentially no gross directional
  content to capture, consistent with the ~0.01 lead correlation.
- Net of cost: ≈ −0.30% with **0/4 walk-forward folds positive** on both alts (fold nets all ≈ −0.30%).

## Conclusion (T1)

At 1-minute resolution **BTC does not robustly lead ETH/SOL in any exploitable way**: co-movement is
contemporaneous (and OHLCV-visible), the residual lead is tiny and directionally ambiguous, and the
tradable signal has zero gross edge and 0/4 folds net of cost. Cross-asset lead-lag is **NO_EDGE** and
adds **no information beyond the contemporaneous co-movement already in OHLCV.** (Sub-minute cross-asset
lead-lag is below this resolution and outside this system's execution reach — explicitly not claimed; see
`phase18_leadlag_architecture.md`.)
