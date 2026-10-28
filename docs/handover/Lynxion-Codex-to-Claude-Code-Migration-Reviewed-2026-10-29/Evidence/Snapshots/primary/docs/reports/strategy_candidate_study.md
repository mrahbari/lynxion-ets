# Strategy Candidate Study (RETIRED-slot replacement)

**Date:** 2026-06-13
**Mandate:** replace **at most two** RETIRED slots (scalping, crypto_breakout) with better-designed
alternatives — *only if evidence justifies it*. Do not modify surviving strategies/params/thresholds.
New strategies must have a clear hypothesis, be architecture-compatible, use available data, not
duplicate existing strategies, and be auditable. **Profitability is not assumed.**

**Prior context (sets the bar):** the deployment-validation re-run showed the *entire* existing suite,
correctly deployed (design-TF + regime-conditioned + per-symbol), has **no positive cross-period-stable
edge net of 0.30% round-trip cost** (0/30 cells READY). Any replacement must clear that same bar.

## Available inputs / architecture constraints
- **Data feeds:** OHLCV at 1m/5m/15m/30m/1h for BTC-USDT, ETH-USDT, SOL-USDT (verified). No reliable
  order-book, funding, or sufficient open-interest history (oi_footprint is data-blocked).
- **Architecture:** `BaseStrategyAdapter` subclass; `update_with_market_data(bar)` builds a per-symbol
  `data_buffer`; `generate_signal(symbol) -> Signal|None`; base provides `calculate_ema/rsi/atr`.
  Signals are **per-symbol** (an adapter sees only its own symbol's buffer) → **cross-asset strategies
  are architecturally incompatible**.
- **Existing coverage (must not duplicate):** trend (trend_following, mtf_trend, momentum), structural
  mean-reversion (mean_reversion), session-VWAP reversion (vwap_reversal), liquidity-sweep fade
  (liquidity, sweep_scalper), range/compression breakout (breakout) + ATR-expansion breakout
  (volatility_breakout), volume-footprint (oi_footprint).

## Candidates studied

### C1 — Short-Term Statistical Reversal (STR) ✅ SELECTED
- **Hypothesis:** at short horizons in **non-trending** regimes, crypto returns show negative
  autocorrelation — an over-extended k-bar move partially reverts. Fade extreme short-term moves.
- **Required inputs:** close prices only (rolling return z-score). OHLCV-available. ✔
- **Intended timeframe:** 15m (cost-viable; short reversal horizon).
- **Intended regime:** ranging (gated out of trends).
- **Expected holding period:** short — 2–4 bars (~30–60 min).
- **Overlap:** *Distinct.* mean_reversion uses **structural range bounds + RSI + failed-expansion**;
  vwap_reversal uses **session-anchored VWAP**. STR is a **pure statistical return-reversal** (z-score
  of returns) with no levels/VWAP. Different signal generator.
- **Implementation complexity:** Low (rolling mean/std of returns; regime gate via sma slope).
- **Validation plan:** BTC/ETH/SOL @15m, regime-conditioned (ranging), 4-fold walk-forward + half-split
  cross-period, net of 0.30% cost.

### C2 — Donchian Channel Breakout (DCB) ✅ SELECTED
- **Hypothesis:** a decisive break of the prior **N-bar high/low channel** (classic turtle channel)
  initiates a directional move that continues (trend-initiation), filtered to expanding volatility.
- **Required inputs:** high/low/close + ATR. OHLCV-available. ✔
- **Intended timeframe:** 1h.
- **Intended regime:** breakout / trend-initiation (volatility expanding).
- **Expected holding period:** 6–12 bars (~6–12 h).
- **Overlap:** *Partial but distinct mechanism.* breakout detects **consolidation compression +
  rejection geometry**; volatility_breakout triggers on **ATR expansion magnitude**. DCB is a **pure
  N-bar channel break** (Donchian/turtle) — a different, simpler, a-priori trigger. Honest note: it is
  the closest to existing breakout strategies; included specifically to test whether the simplest
  classic channel break does better than the elaborate ones.
- **Implementation complexity:** Low (rolling max/min channel + ATR filter).
- **Validation plan:** BTC/ETH/SOL @1h, regime-conditioned (breakout/trend), 4-fold walk-forward +
  half-split, net of cost.

### C3 — Cross-Sectional Relative Strength (BTC/ETH/SOL rotation) ❌ REJECTED
- **Hypothesis:** long the strongest / short the weakest of the three over a lookback.
- **Reject reason:** **architecture-incompatible** — per-symbol adapters cannot see other symbols'
  data; cross-asset portfolio logic does not fit `generate_signal(symbol)`. Violates rule 5
  (architecture compatibility) without a framework change (forbidden — infra frozen).

### C4 — Bollinger %b / band reversion ❌ REJECTED
- **Reject reason:** **duplicate** — a band-based reversion is the same family as mean_reversion (BB +
  RSI) and vwap_reversal (σ-band around VWAP). No distinct hypothesis.

### C5 — Time-of-Day / session seasonality ❌ REJECTED
- **Reject reason:** identifying favourable hours from the data is **curve-fitting / edge discovery
  (forbidden)**; an a-priori hour window is arbitrary and weak. Low auditability of the chosen window.

## Ranking
| Rank | Candidate | Distinct? | Implementable? | A-priori (no fit)? | Decision |
|---|---|---|---|---|---|
| 1 | **C1 Short-Term Statistical Reversal** | yes | yes | yes | **SELECT** |
| 2 | **C2 Donchian Channel Breakout** | partial (distinct mechanism) | yes | yes | **SELECT** |
| 3 | C3 Cross-Sectional RS | yes | **no (incompatible)** | — | reject |
| 4 | C4 Bollinger reversion | no (duplicate) | yes | yes | reject |
| 5 | C5 Time-of-day seasonality | yes | yes | **no (fit risk)** | reject |

## Selection
Implement and validate **C1 (STR)** and **C2 (DCB)** to fill the two RETIRED slots, **provisionally** —
each is retained only if it clears the READY bar (positive expectancy + cross-period stability +
regime consistency + walk-forward) on evidence. Parameters are **a-priori standard values** (no tuning,
no search). If neither clears the bar, the slots stay **empty** (rule 12).

> Honest expectation (not a prejudgement): given the existing suite is uniformly edgeless net of cost
> on the same data, these OHLCV-only candidates are *unlikely* to clear the bar — but the validation
> (next deliverables) will decide, not this expectation.
