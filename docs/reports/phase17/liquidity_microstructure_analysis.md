# Phase 17 — Liquidity Microstructure Analysis & Results

**Date:** 2026-06-13. Analysis only; no strategy/parameter/threshold/risk/execution changes; no
profitability claim. Domain 2 (liquidity microstructure). Data: futures 5m, BTC/ETH/SOL, 2024-06 →
2026-06. A-priori features, not tuned.

## Scope note — what is and isn't testable

True L2 order-book microstructure (resting depth, book imbalance, spread dynamics, stacking/spoofing) has
**no integrated historical source** (REST `/depth` is a snapshot; no historical book) and is therefore
**backtest-blocked** (Phase-13, restated in `phase17_microstructure_architecture.md`). What *is*
buildable historically is a **trade-structure liquidity proxy** from kline trade-count and trade-size
fields. This section tests that proxy and is explicit that it is **not** a test of L2 depth.

## Signal Family B — Liquidity Expansion / Contraction

**Construction (non-OHLCV).** From number-of-trades (kline field [8]) and avg trade size:
- `intensity_z` = z-score of `num_trades` over a 100-bar window → **expansion** (high) vs
  **contraction** (low) of trading activity / liquidity consumption
- `avgtrade_z` = z-score of `volume/num_trades` → block/stacking vs fragmentation

Two a-priori hypotheses:
- **(volatility)** liquidity expansion precedes volatility expansion → predicts forward |return|
- **(directional, gated)** flow signal taken *only* in expansion (vs contraction) regime — does the
  liquidity state improve the order-flow signal?

## Result 1 — Liquidity DOES predict volatility (but redundantly with OHLCV)

Spearman IC vs forward 30-min |return|:

| Feature | BTC | ETH | SOL | reading |
|---|---:|---:|---:|---|
| **`intensity_z` (liquidity expansion)** | **+0.139** | **+0.136** | **+0.122** | genuine, cross-symbol-consistent **volatility** signal |
| `flow_k` (abs) | −0.099 | −0.067 | −0.062 | weak |
| **OHLCV recent \|return\| (baseline)** | **+0.233** | **+0.214** | **+0.187** | **stronger** than liquidity |

- **Liquidity expansion is genuinely informative about forward volatility** (IC ≈ +0.13 on all three
  symbols) — the one clean, cross-symbol-consistent microstructure relationship in Phase 17.
- **But it is weaker than, and redundant with, OHLCV realized volatility** (IC ≈ +0.21), which already
  captures volatility clustering. So even this real signal provides **no incremental volatility
  information beyond OHLCV.**
- **And it is non-directional** — predicting the *size* of the next move is not a tradable directional
  edge by itself; it cannot be converted to expectancy without a direction (which order flow failed to
  provide).

## Result 2 — Liquidity gating does NOT rescue the flow signal (cost-adjusted, 4-fold WFO)

Order-flow signal taken only within each liquidity regime:

| Signal | BTC exp | ETH exp | SOL exp | n (BTC) | WFO |
|---|---:|---:|---:|---:|---|
| flow in **expansion** | −0.3087% | −0.3051% | −0.3025% | 73,586 | **0/4, all-negative** |
| flow in **contraction** | −0.3025% | −0.3035% | −0.3073% | 140,132 | **0/4, all-negative** |

- In **both** liquidity regimes the flow signal still returns ≈ minus the cost (gross ≈ 0), **0/4 folds
  positive on every symbol.** Conditioning on liquidity expansion/contraction adds nothing — the absent
  directional edge stays absent.

## Section conclusion (liquidity microstructure)

The trade-structure liquidity proxy carries a **real but redundant, non-directional** volatility signal
(IC ≈ +0.13, weaker than OHLCV's +0.21) and **does not create or rescue any directional edge**. True L2
depth remains untestable (no history). **No deployable edge; no incremental information beyond OHLCV.**
Consolidated walk-forward → `microstructure_walkforward_results.md`.
