# Symbol-Universe Validation (Phase 12)

**Date:** 2026-06-13
**Question:** Is READY = 0 genuinely strategy-wide, or an artifact of evaluating primarily BTC/ETH/SOL?
**Method:** the 10 active (frozen) strategies, each on its **design timeframe**, **regime-conditioned**,
**per-symbol independently** (no aggregation), net of the existing 0.30% round-trip cost. Metrics per
cell: in-regime expectancy, trade count, win rate, **cost-adjusted (cumulative) return**, **max
drawdown**, **4-fold walk-forward**. No strategy logic/params/thresholds/risk/execution changed.

## Universe & data (honest constraint)
| Symbols | Data |
|---|---|
| BTC, ETH, SOL | full multi-year sets (8.7k 1h / 35k 15m / 105k 5m) — from the prior re-eval |
| BNB, XRP, DOGE, ADA, LINK, TRX, SUI, AVAX | **fetched ~1000 bars each** at 1h/15m/5m (Binance public) |
| **HYPE, TON** | **no data available** (not on the public feeds tried) — excluded |

**Critical caveat:** the 8 new symbols have only ~1000 bars per TF — ~41 days at 1h, ~10 days at 15m,
~3.5 days at 5m — a **short, single-calendar-period** window. Walk-forward over 4 contiguous folds in
one window is a weak OOS test, and design-TF strategies needing 50–160-bar warmup accumulate far fewer
in-regime signals than on the multi-year majors. Results on the new symbols are therefore **lower-power**
and several strategies are **unjudgeable** there. (`scripts/fetch_universe_data.py`,
`scripts/universe_validation.py`; raw `_universe_validation.json` + `_revalidation_results.json`.)

## In-regime expectancy across the 8 new symbols (% net per trade; n<20 = too few to judge)
| Strategy (design TF) | BNB | XRP | DOGE | ADA | LINK | TRX | SUI | AVAX |
|---|---|---|---|---|---|---|---|---|
| trend_following (1h) | −0.14 | **+0.19** | **+0.12** | −0.30 | −0.11 | −0.29 | −0.03 | −0.30 |
| momentum (1h) | −0.30 | **+0.39** | −0.17 | −0.18 | −0.13 | −0.35 | −0.34 | −0.26 |
| mtf_trend (15m) | −0.29 | −0.27 | −0.50 | −0.28 | −0.48 | −0.58 | −0.17 | −0.47 |
| oi_footprint (1h) | −0.24 | **+0.38** | **+0.09** | −0.24 | **+0.04** | −0.24 | −0.10 | −0.12 |
| sweep_scalper (1m→) | −0.26 | −1.28 | −0.69 | −0.14 | −0.55 | −0.20 | −0.27 | −0.70 |
| mean_reversion (1h) | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 |
| breakout (15m) | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 |
| liquidity (5m) | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 |
| vwap_reversal (5m) | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 |
| volatility_breakout (15m) | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 | n<20 |

(BTC/ETH/SOL: all 10 strategies in-regime negative or unstable — see `per_symbol_strategy_results.md`.)

## The positive cells, examined (WFO + drawdown)
| Strategy | Sym | exp% | n | win | cumRet% | maxDD% | WFO +folds | fold expectancy % |
|---|---|---|---|---|---|---|---|---|
| trend_following | XRP | +0.19 | 92 | 0.47 | +17.0 | **−17.3** | 3/4 | −0.80 / +0.06 / +0.39 / **+0.93** |
| trend_following | DOGE | +0.12 | 58 | 0.36 | +6.9 | **−30.1** | 2/4 | −1.60 / −0.83 / +0.77 / +1.19 |
| momentum | XRP | +0.39 | 139 | 0.53 | +54.0 | **−32.4** | 3/4 | +0.08 / −0.52 / +0.29 / **+1.31** |
| oi_footprint | XRP | +0.38 | 110 | 0.48 | +41.6 | −12.0 | **4/4** | +0.37 / +0.18 / +0.01 / **+1.08** |
| oi_footprint | DOGE | +0.09 | 124 | 0.43 | +10.8 | −29.9 | 2/4 | −0.24 / −0.77 / +0.75 / +0.43 |
| oi_footprint | LINK | +0.04 | 112 | 0.53 | +4.8 | −27.9 | 2/4 | −0.49 / −0.11 / +0.20 / +0.60 |

**Reading:** every positive cell is **back-loaded** — the final fold dominates while earlier folds are
flat/negative — with **large drawdowns** (−12% to −32%) and mostly sub-50% win rates. That is the
signature of a strategy catching **one directional episode** in the short window (XRP in particular
trended strongly in the sampled period), **not** a stable, repeatable, cross-period edge. No cell is
positive in a *front-loaded and consistent* way, and none clears the READY bar.

## Answer
**READY = 0 is NOT an artifact of BTC/ETH/SOL.** Across the broader universe:
- Well-powered strategies (trend_following, momentum, mtf_trend, oi_footprint, sweep_scalper) are
  predominantly negative; their isolated positives are short-window, back-loaded, high-drawdown
  episodes (concentrated on XRP) — not repeatable edges.
- Five strategies are **unjudgeable** on the new symbols (too few in-regime signals on ~1000 bars).
- HYPE/TON had no data.

**No strategy is READY on any symbol.** The verdict holds universe-wide. The XRP cluster is flagged as
**asset-specific episodic behavior** worth longer-history investigation (see `asset-class-behavior-report.md`),
but on the available evidence it is INCONCLUSIVE, not an edge. See `strategy-reclassification-v2.md`,
`replacement-strategy-assessment.md`, `final-phase12-verdict.md`.
