# Final Phase-12 Verdict — Strategy Universe Expansion Validation

**Date:** 2026-06-13
**Question:** Is READY = 0 genuinely strategy-wide, or merely an artifact of evaluating primarily
BTC/ETH/SOL?

# Verdict: READY = 0 is genuinely strategy-wide — NOT a BTC/ETH/SOL artifact.

Across an 11-symbol universe (BTC/ETH/SOL full history + BNB/XRP/DOGE/ADA/LINK/TRX/SUI/AVAX), with the
frozen strategies run on their design timeframe, regime-conditioned, per-symbol, net of cost:
**no strategy is READY on any symbol.** Broadening the universe did not overturn READY = 0.

## What the evidence shows
- **Confirmed broadly negative:** mtf_trend and sweep_scalper are negative on **all 8** new symbols
  (and the majors). trend_following, momentum, oi_footprint are negative on most symbols.
- **Isolated positives are episodic, not edges:** the only net-positive cells cluster on **XRP**
  (trend_following +0.19%, momentum +0.39%, oi_footprint +0.38%) with weak echoes on DOGE/LINK. All are
  **back-loaded** (final walk-forward fold dominates, earlier folds flat/negative), carry **−12% to
  −32% drawdowns**, and have ~47–53% win rates — the signature of catching one XRP up-trend in a short
  ~41-day window, not a repeatable cross-period edge. Three strategies agreeing on XRP = they all caught
  the *same* trend, not three independent edges.
- **Several strategies are unjudgeable on the new symbols:** mean_reversion, breakout, liquidity,
  vwap_reversal, volatility_breakout produced too few in-regime signals on the ~1000-bar window →
  **INCONCLUSIVE** there (reclassified accordingly).

## Reclassification v2 (full detail in `strategy-reclassification-v2.md`)
READY 0 · INVALIDATED 5 (trend_following, momentum, mtf_trend, sweep_scalper, oi_footprint) ·
INCONCLUSIVE 4 (mean_reversion, liquidity, vwap_reversal, volatility_breakout) ·
NEEDS_IMPROVEMENT 1 (breakout) · RETIRED 2 (scalping, crypto_breakout).

## Replacement
**None.** No candidate (existing strategy on any symbol, or the Phase-11 STR/Donchian candidates)
exceeds the retired strategies under the full standard. The RETIRED slots remain **empty**
(`replacement-strategy-assessment.md`).

## The one honest caveat (and the only real lead)
The broader-universe test is **data-limited**: the 8 new symbols had only ~1000 bars per TF (≈ 41 days
at 1h), a single calendar window; HYPE and TON had no public data. This makes the new-symbol verdicts
**lower-power** (hence several INCONCLUSIVE) and means "asset-specific behavior" cannot be cleanly
separated from "this symbol trended in the sampled window." The **only** falsifiable lead worth a
future, un-frozen, longer-history follow-up is **trend/momentum-family behavior on XRP (and possibly
DOGE)** — to test whether it is repeatable across regimes or just one episode. On current evidence it is
**INCONCLUSIVE, not READY, and not deployable.**

## Bottom line
- READY = 0 **holds across the broader universe** — it is a property of the strategies (no edge net of
  cost on these assets under the no-tuning constraint), not an artifact of the original 3-symbol set.
- The expansion **surfaced no deployable edge** and **justified no replacement**.
- It **did** surface one data-limited lead (XRP trend/momentum) and exposed a real data gap (short
  history for the broader universe; no HYPE/TON), which is the honest, evidence-based output of this
  phase.

Evidence determined the outcome. Profitability was neither assumed nor its absence assumed — both were
tested; the strategies do not demonstrate an edge, and the one apparent exception is an unconfirmed,
episodic, data-limited signal.

## Artifacts
`symbol-universe-validation.md`, `asset-class-behavior-report.md`, `strategy-reclassification-v2.md`,
`replacement-strategy-assessment.md`, this file. Harnesses: `scripts/fetch_universe_data.py`,
`scripts/universe_validation.py`. Raw: `_universe_validation.json`, `_revalidation_results.json`. No
strategy logic/params/thresholds/risk/execution modified.
