# Phase 16 — Final Strategy Register

**Date:** 2026-06-13. Canonical, closing classification of every strategy. Carried from reclassification
v3 (Phase 15) and the strategy program verdict; reconciles to the program's stated current state
(READY 0 / NEEDS_IMPROVEMENT 1 / INCONCLUSIVE 4 / INVALIDATED 5 / RETIRED 2). No strategy modified.

| # | Strategy | Design TF | Final class | Decisive evidence |
|---|---|---|---|---|
| 1 | trend_following | 1h | **INVALIDATED** | Negative on all symbols net of cost; ≤1/4 WFO folds; XRP/DOGE/LINK positives collapse over 7–9 yr (Phase 15) |
| 2 | momentum | 1h | **INVALIDATED** | Negative on all 5 symbols, **0/4 folds**, n=8k–11k in-regime (Phase 15) |
| 3 | oi_footprint | 1h | **INVALIDATED** | Volume-spike proxy (OI mechanism stubbed); negative all symbols; real OI history caps ~30d → untestable (Phase 15) |
| 4 | mtf_trend | 15m | **INVALIDATED** | Negative on all 8 universe symbols; single-TF EMA, not true MTF (architecture review / Phase 12) |
| 5 | sweep_scalper | 1m | **INVALIDATED** | Negative on all 8 universe symbols; sweep detector stubbed (architecture review / Phase 12) |
| 6 | mean_reversion | 1h | **INCONCLUSIVE** | Structurally frequency-starved: in-regime n=1–9 over 60–77k bars — proven NOT a coverage gap (Phase 15) |
| 7 | vwap_reversal | 5m | **INCONCLUSIVE** | Frequency-starved: in-regime n=0–8 over up to 315k 5m bars (Phase 15) |
| 8 | liquidity | 5m | **INCONCLUSIVE** | Frequency-starved + short window; negative/thin where measurable (Phase 12) |
| 9 | volatility_breakout | 15m | **INCONCLUSIVE** | Positives fail cross-period stability; thin in-regime sample (Phase 12) |
| 10 | breakout | 15m | **NEEDS_IMPROVEMENT** | Untradeable wiring (windowing latch); inconclusive elsewhere |
| 11 | scalping | 1m | **RETIRED** | Cost-NON_VIABLE on 1m; slot kept **EMPTY** |
| 12 | crypto_breakout | 15m | **RETIRED** | Retired; slot kept **EMPTY** |
| — | short_term_reversal (STR) | 15m | **INVALIDATED — not deployed** | Replacement candidate; stable-negative, WFO 0/4 |
| — | donchian_breakout (DCB) | 1h | **INVALIDATED — not deployed** | Replacement candidate; stable-negative, WFO 0–1/4 |

## Tally

| Class | Count | Strategies |
|---|---|---|
| **READY** | **0** | — |
| NEEDS_IMPROVEMENT | 1 | breakout |
| INCONCLUSIVE | 4 | mean_reversion, vwap_reversal, liquidity, volatility_breakout |
| INVALIDATED | 5 | trend_following, momentum, oi_footprint, mtf_trend, sweep_scalper |
| RETIRED (empty) | 2 | scalping, crypto_breakout |

Replacement candidates STR and DCB were implemented and evaluated only — **INVALIDATED, never deployed**.

## Closing note

The defining number is **READY = 0**, and it is not a gap waiting to be filled by more tuning, more
symbols, more data, or more history — each of those was tested and rejected (`program_closure_report.md`).
The register is final for this program.
