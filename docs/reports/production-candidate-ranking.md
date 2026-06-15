# Production Candidate Ranking

**Date:** 2026-06-12. Strategies ranked by **proximity to deployability** on the
re-architected higher timeframes (15m/30m/1h, BTC/ETH/SOL, existing params only).
**No candidate is deployable** (see `final-deployment-readiness-report.md`); this ranking
identifies where the *least-far* opportunities and the *clearest dead ends* are, to focus
any future (non-tuning) work.

Ranking signal = (cost-viable-TF positive cells) × (cross-symbol breadth) × (trade
sample) − (catastrophic-tail severity). Evidence: complete 1h matrix + 15m (106/108).

## Tier 1 — Closest (isolated edge, fails only cross-symbol stability)
1. **oi_footprint** — best single result (ETH 1h 365d **+405, GO**), strong sample (2284
   trades). *Blocker:* BTC/SOL negative; **data dependency** — uses volume×1.5 as an OI
   proxy, so its named edge is unproven without a real OI feed. *Class:* NEEDS_IMPROVEMENT
   (data-blocked). *Highest-value follow-up:* wire real OI, then re-test cross-symbol.
2. **mtf_trend** — most active (3579 trades), BTC 1h marginally + (+9) and a GO cell.
   *Blocker:* ETH/SOL deeply negative; not true MTF (3 EMAs on one TF). *Class:*
   NEEDS_IMPROVEMENT.
3. **momentum** — BTC 1h + (+41), GO cell, decent sample (1628). *Blocker:* ETH/SOL
   negative, SOL catastrophic (−3364). *Class:* NEEDS_IMPROVEMENT.

## Tier 2 — Marginal (small/occasional positives, no breadth)
4. **trend_following** — 2 GO cells, large sample (1436); all-symbol-negative in
   aggregate but least-bad at 1h. NEEDS_IMPROVEMENT.
5. **liquidity** — Type-A fixed (directional coverage restored); ETH + (+58) at both TFs;
   BTC/SOL negative. NEEDS_IMPROVEMENT.
6. **sweep_scalper** — tiny mixed results (SOL 1h +34), low sample (116). NEEDS_IMPROVEMENT.
7. **volatility_breakout** — small negatives across the board, no positive cell.
   NEEDS_IMPROVEMENT.

## Tier 3 — Barely trade at higher TF (frequency-limited)
8. **vwap_reversal** — fires at 1m only; ~0 trades at 1h (multi-condition gates rarely
   co-occur on coarse bars) + documented Type-B dead-rejection path. NEEDS_IMPROVEMENT.
9. **mean_reversion** — ~0 trades at higher TF (conjunction selectivity). NEEDS_IMPROVEMENT.
10. **breakout** / 11. **crypto_breakout** — 0 trades: documented Type-B `min_confidence`
    gate rejects their signals (not changed — would be tuning). NEEDS_IMPROVEMENT pending
    that human-reviewed reclassification.

## Tier 4 — Dead end
12. **scalping** — negative on **every** symbol and **every** timeframe (1m/15m/1h);
    structurally cost-sensitive. **NON_VIABLE.**

## Ranked next-work priorities (all non-tuning)
1. **oi_footprint real-OI data feed** — unblocks the single most promising result.
2. **Cross-symbol stability gating** + **walk-forward** on 1h for Tier-1/2 before any READY.
3. **Human review of breakout B-1 / vwap B-3** (Type-B → possible Type-A) per
   `candidate-calibration-fixes.md`.
4. Prefer **1h** over 15m for any viability work (more cost-robust; 15m sits on the cost
   cliff).

**Bottom line:** the ranking is a map of *least-far*, not *ready*. Even Tier-1 candidates
fail cross-symbol stability; none should see live capital without demonstrated,
out-of-sample, cross-symbol positive expectancy.
