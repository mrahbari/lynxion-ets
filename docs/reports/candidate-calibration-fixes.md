# Candidate Calibration Fixes (Type-B) — DOCUMENTED, NOT IMPLEMENTED

**Date:** 2026-06-12. Per Rehab Mode rules, **Type-B calibration issues are not changed
automatically.** This is the register: evidence, expected upside, hypothesis-drift risk,
affected strategies, recommendation. **No implementation, no threshold change, no tuning,
no optimization, no Hyperopt, no parameter sweeps.** Each requires explicit human review
because each carries hypothesis-drift or curve-fitting risk.

---

## B-1 · breakout / crypto_breakout — confidence-scale vs `min_confidence` gate
- **Evidence:** `generate_signal` produces 13 actionable signals / 20k bars, but
  `evaluate_fused_signal` rejects them (`min_confidence=0.3`) because the confidence
  formula `(compression_ratio/10 + |momentum|)/2` (floored at 0.1) rarely exceeds 0.3 →
  **0 trades** in every backtest cell.
- **Expected upside:** would unblock breakout/crypto_breakout to trade and become
  measurable (currently zero-trade). Profitability upside unknown — under the Type-C 1m
  cost finding it would still likely lose on 1m.
- **Hypothesis-drift risk:** MEDIUM. Lowering `min_confidence` or rescaling the confidence
  formula changes *which* breakouts are admitted — i.e., the selectivity that is part of
  the hypothesis. Could become "loosen entries to force trades" (forbidden).
- **Affected:** breakout, crypto_breakout.
- **Recommendation:** review whether the confidence *formula* is mis-scaled (a defect) vs
  the *threshold* being deliberately strict (hypothesis). If the former, it reclassifies
  to Type-A; if the latter, leave. Decide on a cost-viable timeframe, not 1m.

## B-2 · ATR stop-multiplier (1.5) and RR (1.5) vs cost on sub-15m timeframes
- **Evidence:** SL=1.5×ATR, TP=2.25×ATR. On 1m, TP=0.10% ≪ 0.30% round-trip cost
  (cost-breakeven ≈ 15m). The geometry is sound at ≥15m; it is the *timeframe*, not the
  multiplier, that is wrong on 1m.
- **Expected upside:** raising `atr_multiplier` so targets clear costs on 1m would
  technically allow profit, but at SL≈10–15×ATR the risk geometry and hold time change
  fundamentally — this is no longer the same strategy.
- **Hypothesis-drift risk:** HIGH. Re-sizing stops purely to beat 1m costs is
  optimization-against-costs and changes strategy identity.
- **Affected:** all (shared geometry).
- **Recommendation:** **do not change the multiplier.** Address via timeframe (deploy on
  ≥15m) — see `production-readiness-report.md`. The multiplier is correct for its
  intended (higher) timeframe.

## B-3 · vwap_reversal — dead `_check_rejection_pattern` confirmation path
- **Evidence:** `bullish_rejection` requires close *above* VWAP while the BUY gate requires
  close ≥σ-band *below* VWAP — mutually exclusive, so the rejection path is dead; only
  `failure_swings` confirms (documented in HFR).
- **Expected upside:** restoring a geometrically-consistent rejection (reversal candle at
  the deviation extreme) would raise signal frequency.
- **Hypothesis-drift risk:** MEDIUM-HIGH. Reinterpreting "rejection" is close to redesign;
  needs bar opens and a clear spec to avoid changing the hypothesis.
- **Affected:** vwap_reversal.
- **Recommendation:** treat as a *spec clarification* with human review; borderline
  Type-A (contradiction) vs redesign. Not changed here.

## B-4 · mean_reversion / vwap_reversal — multi-condition frequency on coarse bars
- **Evidence:** both fire on 1m but ~0 trades at 1h (their AND-chains rarely co-occur on
  fewer, larger bars).
- **Hypothesis-drift risk:** HIGH. Relaxing the conjunction = loosening entries (forbidden).
- **Recommendation:** leave; the selectivity is the hypothesis (Type-C if it starves on
  the viable timeframe).

---

**Summary:** 4 Type-B candidates registered, **0 implemented.** B-1 and B-3 are the only
ones with a plausible Type-A reclassification on review; B-2 and B-4 should be addressed
by timeframe/leave-as-is rather than by changing constants. None should be tuned against
historical results.
