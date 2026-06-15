# Phase 8 — breakout Confidence-Gating Correctness Review

**Date:** 2026-06-12. Evidence-based ruling on breakout's confidence gate. No optimization,
no tuning — ruling only.

## The mechanism
- **Entry confidence** (`breakout_strategy_adapter.py` ~l.287/299):
  `final_confidence_factor = min(1.0, (compression_ratio/10 + |momentum|)/2)`, then
  floored: `confidence = min(1.0, max(0.1, final_confidence_factor))`.
- **Admission gate** (`evaluate_fused_signal` ~l.383): reject if
  `confidence < min_confidence` (`BREAKOUT` config `min_confidence = 0.35`; adapter default 0.3).
- **Range trigger** (`_define_range`): requires `compression_ratio > 1.5`
  (`compression_ratio = historical_range / recent_range`).

## Mathematical analysis
For confidence ≥ 0.35:  `(compression_ratio/10 + |momentum|)/2 ≥ 0.35`
⇒ `compression_ratio ≥ 7.0 − 10·|momentum|`.
With per-bar `|momentum|` ≈ 0.001–0.01 (fractional), this needs **compression_ratio ≳ 6.9**
— i.e. the recent range compressed to **≤ 1/7th** of the historical range. But the
strategy's own trigger admits setups at `compression_ratio > 1.5`. So the *entire*
admissible band `compression_ratio ∈ (1.5, ~7)` maps to confidence **0.10–0.15**, all
**below** the 0.35 gate (and below the 0.3 default).

## Empirical measurement (BTC, 20 000 1m bars)
- Emitted BUY/SELL signals: confidence pinned at the **0.100 floor**; observed
  `compression_ratio ≈ 1.64` (just past the 1.5 trigger).
- Signals with confidence ≥ gate: **0**.
- Across all matrices (15m/30m/1h × BTC/ETH/SOL × 90/180/365d): breakout = **0 trades**.

## Ruling
1. **Is the threshold mathematically unreachable?** Not strictly — `compression_ratio ≥ ~7`
   would reach it — but it is **effectively unreachable for the strategy's own qualifying
   setups** (which trigger at >1.5 and produce confidence 0.10–0.15). In practice the gate
   is never satisfied → ~0 trades.
2. **Does the implementation contradict the documented hypothesis?** **Yes.** The hypothesis
   is "trade the break of a compressed range" — i.e. compression>1.5 breaks should be
   tradeable. The confidence *formula* (`/10`) and the *gate* (0.35) are on **incompatible
   scales**, so the strategy systematically rejects its own valid setups. The two halves of
   the entry contract are internally inconsistent.
3. **Correctness defect or intended behavior?** **Correctness defect (Type-B scale
   mismatch).** "Intended" would mean only trading ≥7× compressions — so rare (and still
   floored at 0.10) that the strategy is effectively non-functional; that is not a credible
   design intent. The defect makes breakout **untradeable as wired**.

## Remediation (NOT performed — would be calibration/optimization)
Either rescale the confidence formula (e.g. normalize `compression_ratio` over its
admissible range) **or** lower `min_confidence` to the formula's output range. Both are
**threshold/parameter changes** that Phase 8 forbids; either also risks manufacturing
in-sample trades. **Requires a human correctness ruling**, not autonomous tuning.

## Disposition: **NEEDS_IMPROVEMENT**
Implementation has a documented internal-inconsistency defect (untradeable). Cannot be
fixed within the no-tuning mandate; cannot be evaluated for edge until the gate is
reconciled by a human decision. Not READY (0 trades, no evidence), not RETIRED (a single
bounded calibration reconciliation would make it measurable).
