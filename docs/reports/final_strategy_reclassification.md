# Final Strategy Reclassification (Phase E)

**Date:** 2026-06-13. Classification after re-evaluating each strategy in its **intended environment**
(design TF + regime-conditioned + per-symbol), existing parameters only — no tuning, no logic changes.

**READY criteria (all required, on at least one symbol):** positive in-regime expectancy (net of cost)
**+** cross-period stability **+** regime consistency **+** adequate in-regime sample (≥30 signals).

# READY = 0 (unchanged). The verdict survives correct deployment.

| Strategy | Classification | Basis (design-TF, in-regime, per-symbol) |
|---|---|---|
| **trend_following** | **INVALIDATED** | Large in-regime sample (582–714); expectancy stable-**negative** on BTC (−0.21) & ETH (−0.29); SOL negative/unstable. Directional hypothesis anti-predictive in trending regime net of cost (~31% win). |
| **momentum** | **INVALIDATED** | Largest sample (702–1331 in-regime); stable-**negative on all three** (−0.29/−0.26/−0.35). Continuation hypothesis refuted in its own regime. |
| **mtf_trend** | **INVALIDATED** | (a) core is a single-TF EMA stub (not true MTF; `compute_trend` mock) **and** (b) ~10k in-regime signals/symbol, stable-negative (−0.31/−0.28/−0.31). Both architecturally and empirically invalid. |
| **oi_footprint** | **INVALIDATED** | Never reads OI (volume proxy; empirical OI Δ=0); all-signal negative (−0.34/−0.21/−0.35). Named architecture absent; no edge as the proxy it actually is. |
| **sweep_scalper** | **INVALIDATED** | `detect_sweep()` is a stub (unused); reduced to a range-ratio proxy; stable-negative in-regime (−0.33/−0.27/−0.21). Architecture unimplemented + no edge. |
| **breakout** | **NEEDS_IMPROVEMENT** | In-regime negative everywhere but small sample (80–105) and unstable on ETH/SOL; also untradeable in the live wiring (Type-B confidence-scale defect). Inconclusive rather than firmly refuted; remediation = threshold change (out of scope). |
| **liquidity** | **NEEDS_IMPROVEMENT** | Frequency-starved even at its 5m design TF (34–51 in-regime); negative where measurable, unstable on ETH. Too thin to firmly classify. |
| **volatility_breakout** | **NEEDS_IMPROVEMENT** | Only strategy with any positive in-regime cells (ETH +0.13, SOL +0.34) — but both are **first-half-only and flip sharply negative** (fail stability) on small samples (38–74). No stable edge; inconclusive. |
| **mean_reversion** | **NEEDS_IMPROVEMENT** | Intrinsic selectivity: 1/4/9 total signals at 1h, **0 in its intended (ranging) regime** → genuinely **unjudgeable**. Not refuted, not READY. |
| **vwap_reversal** | **NEEDS_IMPROVEMENT** | Frequency-starved even at 5m (4–7 in-regime signals) → **unjudgeable**. Not refuted, not READY. |
| *scalping* | **RETIRED** (unchanged) | Cost-incompatible on 1m liquid crypto (tick-cost gate correctly refuses; thesis needs a higher-volatility instrument). |
| *crypto_breakout* | **RETIRED** (unchanged) | Code alias of `breakout` — not a distinct strategy. |

## Tally
- **READY: 0**
- **INVALIDATED: 5** — trend_following, momentum, mtf_trend, oi_footprint, sweep_scalper
- **NEEDS_IMPROVEMENT: 5** — breakout, liquidity, volatility_breakout, mean_reversion, vwap_reversal
- **RETIRED: 2** — scalping, crypto_breakout

## What changed vs the architecture review
The architecture review (analysis-only) hypothesized READY = 0 was *predominantly (B) misdeployment*.
The corrected re-evaluation **tests** that and finds:
- **(B) was real but not exculpatory:** strategies did fire mostly outside their regime and off their
  design TF — yet fixing both did **not** reveal an edge.
- **(A) absence of edge is now demonstrated** for the 5 measurable strategies (negative, cross-period-
  stable in-regime expectancy) → moved from MISDEPLOYED to **INVALIDATED**.
- **2 architecturally-stubbed strategies** (mtf_trend, oi_footprint, sweep_scalper — 3 actually) are
  INVALIDATED on both grounds.
- **2 strategies remain genuinely INCONCLUSIVE** (mean_reversion, vwap_reversal) because they are too
  selective to produce a judgeable in-regime sample even on their design TF → NEEDS_IMPROVEMENT, not a
  proven edge.

## Honest scope caveats
- The metric is a **directional signal-quality-with-cost proxy**, not a full path-dependent SL/TP
  backtest. "INVALIDATED" here means the **entry signal is anti-predictive (or edgeless) in its
  intended regime net of cost, cross-period stable**; converting that to profit would require changing
  entry logic — which is **forbidden** under the current freeze.
- The "INVALIDATED" strategies could in principle be re-examined under un-frozen scope (different exit
  models, instruments, or a true MTF/OI implementation), but **no such work was performed** here.
- No strategy code, parameters, or thresholds were modified. The only change is the Phase-A
  evaluation-routing fix (`get_strategy_timeframe`).

## Bottom line
**READY = 0 survives a correct, in-environment, per-symbol, regime-conditioned re-evaluation.** The
deployment was indeed wrong — but correcting it did not uncover a hidden edge. The READY = 0 verdict is
now **evidence-based at the deployment level**, not an artifact of misdeployment.
