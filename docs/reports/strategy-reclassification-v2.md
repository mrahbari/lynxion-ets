# Strategy Reclassification v2 (post broader-universe)

**Date:** 2026-06-13. Classification across the 11-symbol universe with data (BTC/ETH/SOL full +
BNB/XRP/DOGE/ADA/LINK/TRX/SUI/AVAX ~1000 bars; HYPE/TON no data). Categories: INVALIDATED / MISDEPLOYED
/ INCONCLUSIVE / NEEDS_IMPROVEMENT / READY. No strategy modified. **READY requires** positive +
cross-period-stable + regime-consistent + walk-forward, on ≥1 symbol — **met by none**.

| Strategy | v1 (BTC/ETH/SOL) | Broader-universe evidence | v2 classification |
|---|---|---|---|
| trend_following | INVALIDATED | Negative on majors + most alts; XRP/DOGE positives are back-loaded, high-DD single episodes (3/4, 2/4 folds but front folds negative). Well-powered. | **INVALIDATED** (global) — XRP/DOGE flagged INCONCLUSIVE-episodic |
| momentum | INVALIDATED | Negative everywhere except XRP (+0.39, but one fold −0.52, −32% DD, back-loaded). | **INVALIDATED** (global) — XRP INCONCLUSIVE-episodic |
| mtf_trend | INVALIDATED | Negative on **all 8** new symbols + majors; also stubbed (single-TF EMA, not true MTF). | **INVALIDATED** (confirmed broadly) |
| sweep_scalper | INVALIDATED | Negative on **all 8** new symbols (−0.14 to −1.28) + majors; sweep detector stubbed. | **INVALIDATED** (confirmed broadly) |
| oi_footprint | INVALIDATED | Never reads OI (volume proxy). XRP +0.38 (4/4 folds) / DOGE +0.09 / LINK +0.04 — back-loaded, high-DD, sub-50% win; the rest negative. | **INVALIDATED** (architecture) — XRP INCONCLUSIVE-episodic |
| mean_reversion | NEEDS_IMPROVEMENT | New symbols: n<20 in-regime (too selective on ~1000 bars). BTC/ETH/SOL: 0 in-regime. | **INCONCLUSIVE** (unjudgeable; insufficient data everywhere) |
| breakout | NEEDS_IMPROVEMENT | New symbols: n<20 in-regime; BTC/ETH/SOL: negative/unstable, untradeable wiring. | **INCONCLUSIVE / NEEDS_IMPROVEMENT** |
| liquidity | NEEDS_IMPROVEMENT | New symbols (5m, ~3.5d): n<20 in-regime. BTC/ETH/SOL: negative, thin. | **INCONCLUSIVE** (frequency-starved + short window) |
| vwap_reversal | NEEDS_IMPROVEMENT | New symbols (5m): n<20. BTC/ETH/SOL: 4–7 in-regime. | **INCONCLUSIVE** (frequency-starved everywhere) |
| volatility_breakout | NEEDS_IMPROVEMENT | New symbols: n<20 in-regime; BTC/ETH/SOL: positives fail stability. | **INCONCLUSIVE / NEEDS_IMPROVEMENT** |
| *scalping* (retired) | RETIRED | — | RETIRED |
| *crypto_breakout* (retired) | RETIRED | — | RETIRED |

## Tally (v2)
- **READY: 0** (on any symbol)
- **INVALIDATED: 5** — trend_following, momentum, mtf_trend, sweep_scalper, oi_footprint (the first two
  + oi_footprint carry an **INCONCLUSIVE-episodic** flag on XRP/DOGE pending longer data)
- **INCONCLUSIVE: 4** — mean_reversion, liquidity, vwap_reversal, volatility_breakout (insufficient
  in-regime sample on the short new-symbol window and/or globally)
- **NEEDS_IMPROVEMENT: 1** — breakout (untradeable wiring + inconclusive elsewhere)
- **MISDEPLOYED: 0** — the prior "misdeployed" hypothesis was tested and resolved: correct deployment
  did not reveal an edge.
- **RETIRED: 2** — scalping, crypto_breakout

## Notes
- The broader universe **moved nothing toward READY**. It moved several strategies from
  NEEDS_IMPROVEMENT to **INCONCLUSIVE** (honest: the new-symbol window is too short to judge the
  selective strategies), and **confirmed** the INVALIDATED verdicts broadly (mtf_trend, sweep_scalper
  negative on all 8 new symbols).
- The only positives are XRP-clustered, episodic, high-drawdown — flagged for longer-data follow-up,
  **not** reclassified upward.
