# Phase 18 — Lead-Lag Walk-Forward Results (consolidated)

**Date:** 2026-06-13. Analysis only; no profitability claim. Consolidated information content + cost-
adjusted, walk-forward, per-symbol, cross-symbol results for all three lead-lag tests. Cost = 0.30%
round-trip (unchanged). 1-minute data. Raw: `phase18_results.json`.

## Information content (cost-free) — does microstructure carry predictive info OHLCV lacks?

| Test | Lead signal | k=0 corr | lead (k=1) | predictive IC | cross-symbol | non-OHLCV? |
|---|---|---:|---:|---:|:--:|:--:|
| T1 cross-asset | BTC → ETH/SOL | 0.83–0.88 | 0.010–0.019 | (sign ambiguous) | weak | No (co-move is OHLCV) |
| T2 perp-spot | perp → spot | 0.99 | 0.020–0.026 | basis IC −0.014..−0.048 | **yes** | **Yes** |
| **T3 cross-exchange** | **binance → mexc** | 0.98 | **0.028–0.037** | **disp IC +0.07..+0.11** | **yes** | **Yes** |

- **Cross-asset (T1)** co-movement is contemporaneous and OHLCV-visible; the lead is near-noise and
  directionally ambiguous → **no new information.**
- **Perp-spot (T2)** and **cross-exchange (T3)** carry **genuine non-OHLCV information**: perp leads spot,
  basis mean-reverts, and Binance leads MEXC with a **dispersion→catch-up IC ≈ +0.10** — cross-symbol
  consistent. **T3 is the strongest real signal in Phases 17–18.**

## Cost-adjusted deployability + walk-forward (every signal, every symbol)

| Test / signal | gross/bar | net (−0.30%) | WFO folds positive | cross-symbol |
|---|---:|---:|:--:|:--:|
| T1 BTC→ETH | +7.9e-6 | −0.299% | 0/4 | all-negative |
| T1 BTC→SOL | +9.3e-6 | −0.299% | 0/4 | all-negative |
| T2 perp→spot ×3 | ≈ +1.6e-5 | ≈ −0.298% | 0/4 each | all-negative |
| T2 spot→perp ×3 | ≈ +5e-6 | ≈ −0.300% | 0/4 each | all-negative |
| T3 binance→mexc ×3 | ≈ +2.3e-5 | ≈ −0.298% | 0/4 each | all-negative |
| T3 mexc→binance ×3 | ≈ 0 | ≈ −0.300% | 0/4 each | all-negative |

- **Gross expectancy ≈ 0 for every signal** — even the IC≈0.10 cross-exchange catch-up has ~0 gross
  directional expectancy at 1-bar, because the catch-up (~0.01–0.025% dispersion) is far smaller than one
  minute of noise and far below the cost.
- **0/4 walk-forward folds positive on every test × symbol** (fold nets all ≈ −0.30%). Nothing is
  stable-positive net of cost.
- **Cross-symbol:** uniformly negative net of cost.

## The gap between "informative" and "deployable"

Phase 18's distinctive finding: **real, cross-symbol-consistent, non-OHLCV predictive information exists
(T3 dispersion IC ≈ 0.10; perp-leads-spot), yet none is tradable** because:
1. the effects are **sub-spread / sub-cost** (dispersion ~0.01–0.025% vs 0.30% round-trip), and
2. they are **latency-arbitrage** in nature — capturing them needs co-located, fee-advantaged, sub-minute
   execution this system does not have.

So information content ≠ deployable edge. Classification & replacement decision →
`phase18_final_verdict.md`.
