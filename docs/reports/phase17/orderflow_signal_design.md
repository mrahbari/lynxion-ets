# Phase 17 — Order Flow Signal Design & Results

**Date:** 2026-06-13. Analysis only; no strategy/parameter/threshold/risk/execution changes; no
profitability claim. Domain 1 (order/trade flow) + Domain 4 (funding×flow interaction). All feature
constants a-priori, not tuned. Data: futures 5m, BTC/ETH/SOL, 2024-06 → 2026-06 (~213k bars/symbol).

## Signal Family A — Flow Imbalance (the primary microstructure directional signal)

**Construction (non-OHLCV).** From taker-buy volume (kline field [9]):
- per-bar aggressor imbalance `imb = (2·taker_buy_base − volume)/volume`
- `flow_k = mean(imb, last K=6 bars)` — smoothed net taker pressure over 30 min
- `CVD = cumsum(2·taker_buy_base − volume)` (reported as the cumulative form)

Aggressor side is **not** present in OHLCV, so this is a genuine non-OHLCV feature. Two a-priori
directional hypotheses tested (both, to avoid a sign assumption):
- **flow-follow**: net taker buying → continued up-move (momentum of flow)
- **flow-contrarian**: net taker buying → exhaustion → mild reversal

## Result 1 — Information content (cost-free Spearman IC vs forward 30-min return)

| Feature | BTC | ETH | SOL | reading |
|---|---:|---:|---:|---|
| `flow_k` (flow imbalance) | −0.032 | −0.029 | −0.026 | small, **sign-consistent** (buying → mild reversal) |
| `imb` (1-bar) | −0.023 | −0.019 | −0.017 | weaker, same sign |
| **OHLCV recent_ret (baseline)** | **−0.045** | **−0.047** | **−0.032** | **larger** than flow IC, same sign |
| **corr(flow_k, recent_ret)** | **0.58** | **0.58** | **0.58** | flow is ~58% redundant with OHLCV momentum |

**Interpretation — the decisive finding for Domain 1:** flow imbalance carries a *tiny, cross-symbol
consistent* forward signal (IC ≈ −0.03), but it is **58% correlated with the OHLCV recent return** and
its IC is **smaller** than the OHLCV-momentum IC it overlaps with. So flow imbalance is essentially a
**noisier, weaker proxy for the short-term-reversal already visible in OHLCV** — it provides **no
incremental directional information beyond OHLCV.** This directly answers the phase question for order
flow: *not* information OHLCV lacks.

## Result 2 — Cost-adjusted directional expectancy (0.30% round-trip, 4-fold WFO)

| Signal | BTC exp | ETH exp | SOL exp | WFO (folds+/all) |
|---|---:|---:|---:|---|
| A flow-follow | −0.3046% | −0.3041% | −0.3056% | **0/4, all-negative** (all symbols) |
| A flow-contrarian | −0.2954% | −0.2959% | −0.2944% | **0/4, all-negative** (all symbols) |

- Net expectancy sits essentially **at minus the cost** → **gross directional edge ≈ 0** (flow-follow
  gross ≈ −0.005%, flow-contrarian gross ≈ +0.005% per 30 min — economically null).
- It is **not** "a real edge eaten by cost" — there is barely a gross edge to begin with, consistent with
  the IC ≈ −0.03 being mostly OHLCV-redundant noise.
- **0/4 walk-forward folds positive on every symbol** in both directions → no stability to exploit.

## Result 3 — Funding × Flow interaction (Domain 4)

Funding (8h, forward-filled, no-lookahead) regime × `flow_k` sign; raw forward 30-min return (information
measure, no cost):

| Condition | BTC | ETH | SOL | win |
|---|---:|---:|---:|---:|
| extreme_pos funding & flow_buy | −0.008% | −0.004% | −0.010% | 0.48–0.50 |
| extreme_pos funding & flow_sell | +0.006% | +0.007% | +0.009% | 0.51–0.52 |
| extreme_neg funding & flow_buy | −0.003% | +0.004% | −0.001% | 0.49 |
| **extreme_neg funding & flow_sell** | **+0.011%** | **+0.010%** | **+0.011%** | **0.51–0.53** |

- The pattern is the **same mild flow-reversal** (sell-flow → small positive forward, buy-flow → small
  negative) seen in the IC — funding does **not** create a strong interaction; it mostly re-slices the
  flow-reversal effect.
- The single **cross-symbol-consistent** cell is *extreme-negative funding + aggressive selling →
  +0.011% forward* on all three symbols (capitulation bounce) — this **echoes the Phase-14 WEAK
  extreme-negative-funding/BTC-ETH thread**, now with a flow confirmation. **But +0.011% per 30 min is
  ~37× below the 0.30% round-trip cost** → informative, not remotely tradable.

## Section conclusion (order flow + funding×flow)

Order flow carries a **tiny, OHLCV-redundant** directional signal and **no gross edge**; the funding×flow
interaction yields only an economically trivial (cross-symbol-consistent) capitulation-bounce echo of
Phase-14. **No deployable directional edge, and no incremental information beyond OHLCV.** Liquidity
microstructure → `liquidity_microstructure_analysis.md`; consolidated WFO → `microstructure_walkforward_results.md`.
