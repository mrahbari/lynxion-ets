# Phase 7 — Strategy Deep Review

**Date:** 2026-06-12. Strategy-by-strategy review of the 12 production strategies:
intended hypothesis · entry-logic · exit-logic · regime assumptions · symbol robustness ·
timeframe robustness · remaining issues (Type A impl / B calibration / C market-data).
No new edge discovery, no new strategies, no Hyperopt, no parameter sweeps, no curve-fit.

**Shared facts:** exit geometry is centralized (ATR(14, shifted)×`atr_multiplier` stop,
RR via `risk_reward_ratio`, direction-correct) — sound for all. 1m is structurally
cost-incompatible (TP≈0.10% ≪ 0.30% cost); cost-breakeven ≈15m; 1h is the most
cost-robust horizon. Evidence base: `eval_matrix_{15m,30m,1h}.json` (324 cells), `wfo_1h.json`
(144 cells, 4 disjoint OOS segments). **No strategy is positive across all 3 symbols at any
horizon; none is temporally stable in walk-forward (best 2/4 = coin-flip).**

---

### 1. trend_following
- **Hypothesis:** ride established trends; enter on pullbacks within an up/down trend, avoid chop.
- **Entry:** multi-gate AND-chain (choppy filter + established-trend + pullback + MA-align). Correct; `trend_extreme_threshold` 0.99→0.999 fixed (was always-true). Symmetric.
- **Exit/Regime:** ATR stop/TP (sound); trend-regime gating intrinsic.
- **Robustness:** trades all symbols/TFs (2106 trades); all-symbol-negative; WFO BTC 2/4, ETH 2/4, SOL 1/4 — no persistence.
- **Issues:** none Type-A. Edge weakness = **Type C** (no gross trend edge on OHLCV after costs).

### 2. mean_reversion
- **Hypothesis:** fade range extremes back to the mean after failed expansions.
- **Entry:** range-bound + lower/upper rejection + RSI + failed-expansion conjunction. Range-window bug fixed (excl. tested bars); `failed_expansion` 3→1 fixed.
- **Exit/Regime:** ATR stop/TP; requires ranging regime.
- **Robustness:** **6 trades total** across higher TFs — the multi-condition conjunction rarely co-occurs on coarse bars. WFO insufficient (0/0).
- **Issues:** none Type-A remaining. Low frequency = **Type C** (intrinsic selectivity; relaxing = forbidden optimization).

### 3. momentum
- **Hypothesis:** persistent directional momentum continues; enter in the direction of consistent momentum, avoid exhaustion.
- **Entry:** momentum-sign consistency (≥60%), persistence bars, exhaustion/rejection filter. **Direction-symmetric** (sign-based) — the 1m 19B/6S skew is sample/market, not a bug.
- **Exit/Regime:** ATR stop/TP; momentum regime.
- **Robustness:** 2487 trades; BTC 1h marginally + (GO cell), ETH/SOL negative (SOL −3364). WFO BTC 2/4, ETH 2/4, SOL 0/4.
- **Issues:** none Type-A. **Type C** — edge not stable cross-symbol.

### 4. scalping  → see disposition (RETIRE)
- **Hypothesis:** capture many small moves **only when move > round-trip cost**.
- **Entry:** micro-conditions + tick-cost gate (move ≥ ~0.2%) + MA/momentum/RSI. Volume-units bug fixed (now reaches gate).
- **Exit/Regime:** tight ATR stop/TP.
- **Robustness:** trades at ≥15m (2025) but **negative on every symbol and every timeframe**; cost gate refuses on 1m by design. WFO BTC 0/4, ETH 2/4, SOL 0/4.
- **Issues:** **Type C structural** — its thesis (move>cost at scalp frequency) is unmet by the data at any tradeable frequency. Overwhelming non-viability.

### 5. breakout
- **Hypothesis:** trade the break of a compressed consolidation range.
- **Entry:** latched range (excl. current bar) + compression>1.5 + break + confirmation. Range/threshold/windowing fixed.
- **Critical issue (Type B, internal inconsistency):** confidence = `min(1, (compression_ratio/10 + |momentum|)/2)` floored at 0.1 → realistically ≤~0.15–0.2, but the strategy's own `min_confidence=0.35` gate rejects it → **0 trades at every TF.** The confidence *formula* cannot satisfy the strategy's *own* threshold. Remediation = rescaling the formula or lowering the threshold — a **calibration change** (Phase-7 disallows threshold optimization), so **documented, not changed** (see issue registry / `candidate-calibration-fixes.md` B-1). Needs human correctness ruling.
- **Issues:** Type-B (untradeable-as-wired). Cannot be evaluated for edge until resolved.

### 6. liquidity
- **Hypothesis:** fade liquidity sweeps (stop-runs beyond swing highs/lows) back into range.
- **Entry:** swing-level detection + sweep + close-back-inside confirmation. **Type-A directional bug FIXED** (swing levels missing `'type'` → SELL-only → now 61B/24S).
- **Exit/Regime:** ATR stop/TP; session-aware.
- **Robustness:** 474 trades; ETH + small, BTC/SOL negative. WFO ETH 1/1 (tiny sample), else 0.
- **Issues:** none Type-A remaining. **Type C** — no stable edge.

### 7. mtf_trend
- **Hypothesis:** multi-timeframe trend alignment (higher-TF trend filters lower-TF entry).
- **Entry:** EMA alignment. **Structural limitation (Type C):** "MTF" is approximated by **3 EMAs on a single timeframe**, not true multi-timeframe data — so it is a single-TF EMA-trend strategy, not genuine MTF. (Not an implementation *defect* — it's the implemented design; true MTF would be new logic, disallowed.)
- **Robustness:** most active (5107 trades); BTC 1h marginally + (GO), ETH/SOL deeply negative. WFO BTC 1/4, ETH 1/4, SOL 0/4.
- **Issues:** **Type C** (single-TF proxy; no stable edge).

### 8. oi_footprint
- **Hypothesis:** open-interest footprint (OI build-up/flush) predicts continuation/reversal.
- **Entry:** OI-delta + volume + price. **Data limitation (Type C):** no real open-interest feed — uses **volume×1.5 as an OI proxy**, so the named edge is unproven by construction.
- **Robustness:** 3204 trades; **best single cell ETH 1h +405 (GO)**; BTC/SOL negative. WFO ETH 2/4, BTC 0/4, SOL 1/4.
- **Issues:** **Type C (data)** — cannot realize its hypothesis without a real OI feed. Highest-value data dependency to resolve.

### 9. sweep_scalper
- **Hypothesis:** scalp the reaction to liquidity sweeps (faster cousin of liquidity).
- **Entry:** sweep detection + fast reaction. (`detect_sweep` stub historically unused.)
- **Robustness:** 225 trades; small mixed (SOL 1h +34). WFO ≤1/1.
- **Issues:** low sample; no Type-A confirmed. **Type C** — insufficient/again no stable edge.

### 10. vwap_reversal
- **Hypothesis:** revert to session VWAP when significantly deviated in a mean-reversion regime.
- **Entry:** σ-band deviation + regime + rejection/failure-swing. **Type-A FIXED** (slope unit-bug, `%24` session). Residual **Type-B**: `_check_rejection_pattern` requires close on the opposite VWAP side from the entry → rejection path dead, only failure-swings confirm (documented B-3; fixing borders on redesign).
- **Robustness:** 12 trades at higher TF (fires mainly on 1m). WFO 0/0.
- **Issues:** Type-B residual; **Type C** low frequency on coarse bars.

### 11. volatility_breakout
- **Hypothesis:** enter on volatility expansion / ATR breakout.
- **Entry:** ATR-based breakout signal (implemented this program). Symmetric.
- **Robustness:** 236 trades; small negatives across symbols, no positive cell. WFO 0/0.
- **Issues:** none Type-A. **Type C** — no edge.

### 12. crypto_breakout  → see disposition (RETIRE)
- **Reality:** registered as an **explicit alias of `BreakoutStrategyAdapter`** (`strategy_provider.py:49` "Alias for crypto breakout") — **identical code, config, and results** to `breakout` (0 trades). Not a distinct strategy.
- **Issues:** redundant duplicate. Overwhelming evidence to retire as a separate entry.

---

## Summary of remaining issues by class
- **Type A (implementation):** none remaining — all found defects (liquidity directional, vwap slope/session, scalping/mean_reversion/breakout-range/trend_following gates) are fixed.
- **Type B (calibration):** breakout confidence-vs-`min_confidence` internal inconsistency (B-1); vwap_reversal dead rejection path (B-3). Both documented, **not changed** (remediation = threshold/redesign, disallowed).
- **Type C (market/data):** the dominant class — no gross/stable edge on OHLCV after costs (all), single-TF "MTF" proxy (mtf_trend), volume-based OI proxy (oi_footprint), cost-structural scalping, intrinsic low frequency (mean_reversion/vwap_reversal).
