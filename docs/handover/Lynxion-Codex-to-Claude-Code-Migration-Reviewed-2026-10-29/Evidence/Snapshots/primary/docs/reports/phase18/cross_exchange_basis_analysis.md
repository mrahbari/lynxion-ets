# Phase 18 — Perp-Spot & Cross-Exchange Lead-Lag (T2, T3)

**Date:** 2026-06-13. Analysis only; no strategy/parameter/threshold/risk/execution changes; no
profitability claim. T2 = Binance perp vs Binance spot (~90d, 1m). T3 = Binance futures vs MEXC spot
(~29d overlap, the limit of MEXC 1m retention). Cost-free lead-lag + basis/dispersion IC, plus
cost-adjusted (0.30%) deployability and 4-fold walk-forward, per-symbol.

## T2 — Perp-Spot lead-lag & basis

Lagged cross-correlation `corr(leader[t−k], follower[t])`, k=1 shown (k=0 ≈ 0.99 for all):

| Symbol | perp→spot k=1 | spot→perp k=1 | basis mean | IC(basis → fwd perp ret) |
|---|---:|---:|---:|---:|
| BTC | **+0.026** | +0.007 | −0.050% | −0.018 |
| ETH | **+0.020** | +0.007 | −0.050% | −0.014 |
| SOL | **+0.026** | +0.016 | −0.058% | −0.048 |

- **Perp leads spot** on all three symbols (perp→spot k=1 ≈ 0.02–0.026 > spot→perp ≈ 0.007–0.016) — a
  real, cross-symbol-consistent microstructure fact (futures price discovery leads spot). **Not visible in
  a single OHLCV series.**
- **Basis mean-reverts**: IC(basis → next-bar perp return) is negative on all three (−0.014 to −0.048) —
  a positive basis precedes a mild negative perp move. Cross-symbol consistent.
- **But both are tiny.** k=0 correlation is 0.99 (perp and spot are essentially the same minute-to-minute);
  the lead is ~0.02 and the basis itself averages ~−0.05%.

Cost-adjusted (trade follower in leader's prior direction):

| Signal | gross/bar | net (−0.30%) | win | WFO folds+ |
|---|---:|---:|---:|:--:|
| perp→spot (BTC/ETH/SOL) | ≈ +0.0000158 | ≈ −0.2984% | 0.45–0.49 | 0/4 (all) |
| spot→perp (BTC/ETH/SOL) | ≈ +0.0000050 | ≈ −0.2995% | 0.45–0.48 | 0/4 (all) |

→ gross ≈ 0, net ≈ −cost, **0/4 folds** everywhere. Real signal, **not deployable**.

## T3 — Cross-Exchange lead-lag & dispersion (the strongest signal found)

Lagged cross-correlation, k=1 shown (k=0 ≈ 0.98 for all):

| Symbol | binance→mexc k=1 | mexc→binance k=1 | dispersion σ | **IC(dispersion → fwd MEXC ret)** |
|---|---:|---:|---:|---:|
| BTC | **+0.037** | +0.006 | 0.011% | **+0.103** |
| ETH | **+0.035** | +0.005 | 0.015% | **+0.113** |
| SOL | **+0.028** | +0.006 | 0.025% | **+0.070** |

- **Binance clearly leads MEXC** (binance→mexc k=1 ≈ 0.03–0.037 ≫ mexc→binance ≈ 0.006) on all three
  symbols — the dominant venue leads the smaller one, exactly as price-discovery theory predicts.
- **Cross-exchange dispersion predicts MEXC's next move with IC ≈ +0.07 to +0.11** — when Binance has
  moved away from MEXC, MEXC catches up. This is the **largest, cleanest, most cross-symbol-consistent
  predictive signal in the entire microstructure investigation (Phases 17–18)**, and it is **genuinely
  non-OHLCV**: it cannot be computed from MEXC's own OHLCV — it requires the cross-venue comparison.

**This is real predictive information that OHLCV does not contain.** However:

| Signal | gross/bar | net (−0.30%) | win | WFO folds+ |
|---|---:|---:|---:|:--:|
| binance→mexc (BTC/ETH/SOL) | ≈ +0.0000234 | ≈ −0.2977% | 0.46–0.51 | 0/4 (all) |
| mexc→binance (BTC/ETH/SOL) | ≈ 0 | ≈ −0.300% | 0.44–0.48 | 0/4 (all) |

- The catch-up lives **inside the dispersion itself (~0.01–0.025%)**, which is *smaller than MEXC's spread
  plus the 0.30% round-trip cost.* So gross expectancy ≈ 0 and net ≈ −cost, **0/4 folds** on every symbol.
- It is a **latency-arbitrage effect**: capturing it requires reacting to Binance and trading MEXC inside
  one minute at sub-cost — i.e. co-located, fee-advantaged execution this system does not have.

## Conclusion (T2, T3)

Both perp-spot and cross-exchange relationships contain **genuine, cross-symbol-consistent, non-OHLCV
predictive information** (perp-leads-spot, basis mean-reversion, and especially the **cross-exchange
catch-up, IC ≈ 0.10**). **None is deployable** for this system: the effects are sub-spread / sub-cost,
gross edge ≈ 0, 0/4 walk-forward folds net of cost. Real information, no tradable edge. Consolidated →
`leadlag_walkforward_results.md`; classification → `phase18_final_verdict.md`.
