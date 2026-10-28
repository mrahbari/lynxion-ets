# Strategy Readiness Matrix

**Date:** 2026-06-12. Evidence-based final classification of the 12 production
strategies. **READY requires profitability evidence** (positive expectancy + sufficient
sample + stable behavior + correct implementation). A correct-but-losing strategy is
**NEEDS_IMPROVEMENT**, never READY. Structural market/timeframe incompatibility →
**NON_VIABLE**.

Sources: `eval_matrix.json` (1m), `eval_matrix_1h.json` (1h, 108 cells),
`eval_matrix_15m.json` (15m), `signal_frequency_diagnostic.py`,
`strategy-rehabilitation.md`, `hypothesis-fidelity-review.md`.

## 10-dimension scorecard (✓ pass / ✗ fail / ~ partial)

| strategy | 1 sig-freq | 2 trade-freq | 3 long-cov | 4 short-cov | 5 regime-cov | 6 stop | 7 TP | 8 RR | 9 timeframe | 10 data-suff | profitable? |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| trend_following | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 1m | ✓ | ✗ |
| mtf_trend | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 1m | ✓ | ✗ (BTC+ only) |
| oi_footprint | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 1m | ✓ | ✗ (ETH+ only); no real OI |
| momentum | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 1m | ~ | ✗ (BTC+ only) |
| volatility_breakout | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 1m | ✓ | ✗ |
| liquidity | ✓ | ~ | ✓(fixed) | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 1m | ~ | ✗ (ETH+ only) |
| sweep_scalper | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 1m | ~ | ✗ |
| vwap_reversal | ~ | ✗@1h | ✓ | ✓ | ~ | ✓ | ✓ | ✓ | ✗ 1m | ✗ | ✗ |
| mean_reversion | ~ | ✗ | ✓ | ✓ | ~ | ✓ | ✓ | ✓ | ✗ 1m | ✗ | ✗ |
| breakout | ~ | ✗ (B-gate) | ✓ | ✓ | ~ | ✓ | ✓ | ✓ | ✗ 1m | ✗ | ✗ |
| crypto_breakout | ~ | ✗ (B-gate) | ✓ | ✓ | ~ | ✓ | ✓ | ✓ | ✗ 1m | ✗ | ✗ |
| scalping | ✗@1m | ✗@1m | ✓ | ✓ | ✓@1h | ✓ | ✓ | ✓ | ✗ structural | ~ | ✗ (all−, all TF) |

_Dims 6/7/8 pass: stops/targets are ATR(14)-shifted, RR 1.5:1, direction-correct
(shared, lookahead-safe). Dim 9 fails for all on 1m (cost-incompatible); scalping fails
structurally (loses at every TF). No strategy passes "profitable"._

## Final classification

| strategy | verdict | basis |
|---|---|---|
| trend_following | **NEEDS_IMPROVEMENT** | correct, measurable; net-negative; no stable edge |
| mtf_trend | **NEEDS_IMPROVEMENT** | correct; BTC-only positive, SOL catastrophic (unstable) |
| oi_footprint | **NEEDS_IMPROVEMENT** | correct; ETH-only positive; **data-blocked** (no real OI) |
| momentum | **NEEDS_IMPROVEMENT** | correct; BTC-only positive, SOL catastrophic |
| volatility_breakout | **NEEDS_IMPROVEMENT** | correct; net-negative all symbols |
| liquidity | **NEEDS_IMPROVEMENT** | Type-A fixed; ETH-only positive; no stable edge |
| sweep_scalper | **NEEDS_IMPROVEMENT** | correct; small/mixed; insufficient stable edge |
| vwap_reversal | **NEEDS_IMPROVEMENT** | Type-A fixed; fires @1m only; Type-B residual; no edge |
| mean_reversion | **NEEDS_IMPROVEMENT** | correct; low frequency; no edge |
| breakout | **NEEDS_IMPROVEMENT** | Type-B confidence-gate blocks trades (documented) |
| crypto_breakout | **NEEDS_IMPROVEMENT** | alias of breakout; same Type-B |
| scalping | **NON_VIABLE** | structural cost-incompatibility: refuses @1m, all-negative @15m/1h every symbol |

**READY: 0 · NEEDS_IMPROVEMENT: 11 · NON_VIABLE: 1.**

No strategy meets the READY bar: none has positive expectancy that is stable across
symbols and windows with sufficient sample. The rehabilitation made the set **correct and
measurable** (all Type-A defects removed) but **not profitable** — so the honest verdict
is NEEDS_IMPROVEMENT for the measurable-but-unprofitable majority and NON_VIABLE for the
one strategy with demonstrated structural incompatibility.
