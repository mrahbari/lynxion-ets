# Asset-Class Behavior Report (Phase 12)

**Date:** 2026-06-13. Goal: identify whether any frozen strategy exhibits **repeatable behavior on a
specific asset (class)** even if it fails globally. Per-symbol, design-TF, regime-conditioned, net of
cost. **Data caveat:** the 8 new symbols have only ~1000 bars per TF (short, single-period window), so
"repeatable" can only be probed via 4 contiguous walk-forward folds — a weak test (see
`symbol-universe-validation.md`).

## Asset grouping (as evaluated)
- **Majors:** BTC, ETH (+ BNB).
- **Large alts:** XRP, ADA, LINK, TRX, AVAX, SOL.
- **High-beta / memetic:** DOGE, SUI.
- **No data:** HYPE, TON.

## What clustered
**1. A positive cluster on XRP.** trend_following (+0.19%), momentum (+0.39%), and oi_footprint
(+0.38%) were all net-positive on XRP in-regime — three independent trend/momentum/volume strategies
agreeing on one symbol. This is the single most notable cross-strategy pattern in the universe.

**2. …but it is an episode, not an edge.** All three XRP positives are **back-loaded** (the last
walk-forward fold dominates; earlier folds flat/negative) with **−17% to −32% drawdowns** and ~47–53%
win rates. XRP trended strongly during the sampled ~41-day window; trend/momentum/volume strategies
mechanically profit from *any* sustained directional move. The agreement across three strategies is
evidence they all caught the **same** XRP trend, not that each has an independent edge. A front-loaded,
low-drawdown, all-folds-positive pattern would indicate an edge — this is the opposite.

**3. Weak echoes on DOGE/LINK.** oi_footprint DOGE (+0.09), LINK (+0.04), trend_following DOGE (+0.12)
— tiny positives, 2/4 folds, large drawdowns (−28% to −30%). Same episodic character, weaker.

**4. Majors and the rest: negative.** BTC/ETH/SOL (full data) negative/unstable for all strategies
(prior re-eval); BNB, ADA, TRX, SUI, AVAX negative on the new run. No asset besides XRP shows even a
surface-level positive cluster.

**5. sweep_scalper is uniformly bad across alts** (−0.14 to −1.28), worst on XRP (−1.28) — its stubbed
"sweep" logic over-fires and bleeds cost on every alt.

## Asset-class conclusion
- **No strategy shows *repeatable* (cross-fold, front-to-back consistent, low-drawdown) behavior on any
  asset or asset class.** The only candidate pattern — the XRP trend/momentum/OI cluster — is a single
  directional episode within a short window, not repeatability.
- **There is a defensible, falsifiable lead:** trend/momentum-family strategies on XRP (and to a lesser
  extent DOGE) over a longer, multi-regime history. It is **not** actionable on current evidence (one
  episode, high drawdown), but it is the one place a longer-data follow-up could be informative.
- **Asset class did not rescue any strategy.** The READY-blocking pattern (no positive cross-period-
  stable in-regime edge net of cost) is present in majors and alts alike.

> Honest framing: with only ~41 days of 1h history on the new symbols, "asset-specific behavior" cannot
> be distinguished from "this symbol happened to trend in the sampled window." The correct next step (if
> ever un-frozen) is to acquire multi-year history for XRP/DOGE and re-test trend/momentum there — not to
> deploy anything on the current episodic signal.
