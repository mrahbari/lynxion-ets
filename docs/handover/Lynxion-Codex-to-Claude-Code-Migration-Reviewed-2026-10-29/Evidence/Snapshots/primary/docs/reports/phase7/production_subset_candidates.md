# Phase 7 — Production Subset Candidates

**Date:** 2026-06-12. Question: **can any subset of the existing 12 strategies realistically
become READY?** (READY = profitable + stable across symbols + stable across horizons +
statistically supported, achievable **without** tuning/optimization/curve-fitting.)

## Answer: **No subset is production-ready, and none is on a near-term READY path.**

### Why no subset qualifies now
- **Out-of-sample test is decisive and negative.** Across 4 disjoint quarters × 3 symbols
  at 1h (the most cost-robust TF), **zero (strategy, symbol) pairs are positive in ≥3 of
  4 segments.** The best is 2/4 — statistically a coin-flip. A READY subset would need
  members that are positive across symbols *and* persistent across segments; none exists.
- **No diversification rescue.** The few positives are disjoint and symbol-specific
  (oi_footprint→ETH, momentum/mtf_trend/trend_following→BTC) and all collapse on SOL. A
  portfolio of symbol-specific, non-persistent positives does not net to a stable edge —
  combining them inherits the SOL losses and the period-instability.

### Conditional watchlist (NOT candidates — contingent on non-tuning prerequisites)
These are the *only* members with any positive out-of-sample signal; each is gated on a
**data/validation** step (not parameter optimization). They remain NEEDS_IMPROVEMENT
until/unless the prerequisite is met **and** they then pass a cross-symbol + cross-segment
gate:

| candidate | positive signal | hard prerequisite (non-tuning) | current status |
|---|---|---|---|
| oi_footprint | ETH 1h +405 (GO); WFO 2/4 ETH | **real open-interest feed** (replace volume×1.5 proxy), then re-test | data-blocked; fails cross-symbol/WFO today |
| momentum | BTC 1h +; WFO 2/4 BTC&ETH | cross-symbol + walk-forward gate on 1h | fails SOL + persistence today |
| trend_following | 2 GO cells; WFO 2/4 BTC&ETH | cross-symbol + walk-forward gate on 1h | fails persistence today |

**Promotion rule (for the future, not executed here):** a watchlist member may move toward
READY only if, on ≥1h with existing parameters, it is (a) positive on BTC **and** ETH
**and** SOL, and (b) positive in ≥3 of 4 disjoint OOS segments, and (c) statistically
supported (sufficient trades). None meets (a) or (b) today.

### Excluded from any subset
- **scalping, crypto_breakout** → RETIRED (see final decision).
- **breakout** → untradeable as wired (B1); cannot be a candidate until that correctness
  question is resolved by a human (a calibration decision outside Phase-7 autonomy).
- **mean_reversion, vwap_reversal, sweep_scalper, volatility_breakout, liquidity, mtf_trend**
  → no positive out-of-sample signal and/or sample-starved.

## Conclusion
The realistic production subset today is **empty (size 0)**. The most credible *future*
path is **oi_footprint with a real OI feed**, validated under the promotion rule — but that
is a data-acquisition + validation task, explicitly **not** strategy creation or
optimization, and its success is unproven. Recommend **deploying nothing** and treating the
3-name watchlist as research-gated, not production-bound.
