# Strategy Deployment Validation

**Date:** 2026-06-13
**Question:** Does the READY = 0 verdict survive when each strategy is evaluated in its **intended
deployment environment** (design timeframe + regime-conditioned + per-symbol)?
**Constraints honoured:** no parameter tuning, no threshold changes, no hyperopt, no signal redesign,
no edge discovery, no strategy replacement. Existing production parameters only. The only code change
is an **evaluation-routing fix** (Phase A); strategy logic is untouched.

# Verdict: ✅ READY = 0 SURVIVES — and emphatically.

Across **30 cells (10 strategies × BTC/ETH/SOL)**, evaluated on each strategy's **design timeframe**,
**restricted to its intended regime**, net of realistic round-trip cost:
- **0 cells** meet the READY bar (positive expectancy **+** cross-period stable **+** adequate
  in-regime sample);
- **2 cells** are positive-but-**unstable** (positive in one period, negative the other → overfit
  noise);
- **19 cells** are negative (mostly cross-period-stable negative);
- **9 cells** are **unjudgeable** (too few in-regime signals to evaluate).

Correct deployment did **not** reveal a hidden edge. The architecture review's hypothesis — that
READY = 0 was mostly *(B) misdeployment* — is now **tested and largely rejected for the measurable
strategies**: deployed correctly, they still have no edge. A minority remain genuinely inconclusive
(too selective to judge).

---

## Phase A — Deployment correction (the timeframe layer)

**Finding (verified):** `StrategyConfig.get_strategy_timeframe(strategy_name, default)` **ignored
`strategy_name`** and returned the single global `settings.strategy.timeframe` (e.g. `1m` in the
dev/live profiles) — so every strategy was forced onto one timeframe.

**Fix (routing only, no parameters changed):** added `StrategyConfig.DESIGN_TIMEFRAMES` (the
strategies' already-declared design TFs) and made the accessor route per-strategy. Verified:

| Strategy | Design TF now routed |
|---|---|
| scalping, sweep_scalper | 1m |
| liquidity, vwap_reversal | 5m |
| breakout, volatility_breakout, mtf_trend | 15m |
| trend_following, mean_reversion, momentum, oi_footprint | 1h |

No strategy logic, parameters, or thresholds were modified.

## Methodology (Phases B–D)

- **Engine:** the **real** production strategy adapters (`adapter.update_with_market_data(bar)` →
  `adapter.generate_signal(symbol)`), driven on **design-TF** OHLCV (`data/history/raw/<tf>/<sym>.csv`),
  **per symbol independently**. Harness: `scripts/strategy_deployment_revalidation.py`.
- **Metric:** net forward-return expectancy per actionable signal — `side × fwd_return(horizon) −
  round_trip_cost`, with `round_trip_cost = 2×(fee 0.001 + slippage 0.0005) = 0.30%` (existing params).
  Holding horizon matched to the design TF (1h→6 bars, 15m→8, 5m→12, 1m→15). This is an
  assumption-light **signal-quality-with-cost** proxy — no per-strategy SL/TP simulation, no tuned
  parameters. It measures whether a **directional edge survives net of cost in the intended
  environment**; it is not a path-dependent P&L backtest.
- **Regime conditioning (Phase B):** a transparent, lookahead-safe per-bar labeler (sma20/sma50 trend +
  ATR-expansion for breakout) tags each bar `trending_up/down`, `ranging`, or `breakout`; in-regime
  expectancy counts only signals fired in the strategy's intended regime.
- **Per-symbol (Phase C):** BTC, ETH, SOL reported independently — **never pooled**; SOL does not veto
  BTC/ETH.
- **Stability:** sign agreement of in-regime expectancy across the first vs second half of the window.
- **READY bar:** positive in-regime expectancy **AND** cross-period stable **AND** ≥30 in-regime
  signals.

## Overall results (design TF, all-signal + in-regime expectancy, % net per trade)

| Strategy | TF | BTC all / in-reg | ETH all / in-reg | SOL all / in-reg | Note |
|---|---|---|---|---|---|
| trend_following | 1h | −0.28 / **−0.21** | −0.27 / **−0.29** | −0.19 / −0.16 (flip) | in-regime stable-negative BTC/ETH |
| momentum | 1h | −0.28 / **−0.29** | −0.30 / **−0.26** | −0.30 / **−0.35** | stable-negative all 3 (large n) |
| mtf_trend | 15m | −0.30 / **−0.31** | −0.28 / **−0.28** | −0.30 / **−0.31** | stable-negative; core is a single-TF stub |
| oi_footprint | 1h | −0.34 | −0.21 | −0.35 | never reads OI; 0 in-regime by construction |
| sweep_scalper | 1m | −0.34 / −0.33 | −0.28 / −0.27 | −0.07 / −0.21 | stable-negative; sweep detector stubbed |
| breakout | 15m | −0.30 / −0.45 | −0.24 / −0.16 (flip) | −0.28 / −0.37 (flip) | small in-regime n (80–105); negative |
| liquidity | 5m | −0.25 / −0.28 | −0.34 / −0.30 (flip) | −0.38 / −0.36 | small in-regime n (34–51); negative |
| volatility_breakout | 15m | −0.22 / −0.22 | −0.26 / +0.13 (FLIP) | −0.12 / +0.34 (FLIP) | ETH/SOL positives are first-half only → unstable |
| mean_reversion | 1h | 1 sig | 4 sig | 9 sig | **0 in-regime** — unjudgeable (selectivity) |
| vwap_reversal | 5m | 43 sig / 5 in-reg | 36 / 4 | 38 / 7 | unjudgeable (frequency-starved even @5m) |

(Full per-cell numbers incl. win-rate and half-period splits: `_revalidation_results.json`;
per-symbol breakdown: `per_symbol_strategy_results.md`; regime detail: `regime_conditioned_results.md`.)

## Answer to the mission question

**The edge does not appear under correct deployment.** Of the strategies with enough in-regime signals
to judge (trend_following, momentum, mtf_trend, sweep_scalper, breakout, liquidity, volatility_breakout):
all are negative or have only unstable (first-half-only) positives. The two strategies that could *not*
be judged (mean_reversion, vwap_reversal) are too selective to produce a verdict even at their design
TF. **No strategy meets READY on any symbol.**

This **revises** the architecture review: that review correctly identified misdeployment, but the
corrected re-evaluation shows the misdeployment was **not masking an edge** — for the measurable
strategies the result is **(A) absence of edge**, now demonstrated in the intended environment rather
than assumed. See `final_strategy_reclassification.md`.

> Caveat (honest): this is a directional signal-quality-with-cost proxy, not a full SL/TP backtest. A
> "stable-negative directional expectancy in the intended regime" means the entry signal is
> anti-predictive net of cost there — salvage would require changing entry logic (out of scope/frozen).
