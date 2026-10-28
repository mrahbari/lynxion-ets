# New Strategy Implementation (RETIRED-slot candidates)

**Date:** 2026-06-13. Two selected candidates (`strategy_candidate_study.md`) were implemented and
evaluated. **Neither is deployed** — both failed the READY bar (`new_strategy_validation.md`); they are
retained as documented, tested, evaluated candidates only. No existing strategy/param/threshold was
touched.

## What was implemented
| Candidate | File | Class | Design TF | Intended regime |
|---|---|---|---|---|
| C1 Short-Term Statistical Reversal | `infrastructure/strategies/adapters/short_term_reversal_strategy_adapter.py` | `ShortTermReversalStrategyAdapter` | 15m | ranging |
| C2 Donchian Channel Breakout | `infrastructure/strategies/adapters/donchian_breakout_strategy_adapter.py` | `DonchianBreakoutStrategyAdapter` | 1h | breakout / trend-initiation |

Both subclass `BaseStrategyAdapter` (architecture-compatible), consume the per-symbol `data_buffer`
(OHLCV only — available feeds), and emit a domain `Signal` exactly like the existing adapters
(`signal_type`, `confidence`, `score`, `source_layer`, `metadata`). They use **a-priori standard
parameters** (no tuning, no search):

- **STR:** z-score of the latest 1-bar return over a 20-bar window; entry at ±2.0σ; ranging gate via a
  flat sma20-vs-sma50 separation (<0.4%). Fade the extension (z≥+2 → SELL, z≤−2 → BUY).
- **DCB:** break of the prior 20-bar high/low channel, gated to expanding volatility (ATR > 1.1× its
  100-bar median). Break up → BUY, break down → SELL.

## Configuration
Added design-TF routing only: `StrategyConfig.DESIGN_TIMEFRAMES` gains `short_term_reversal: 15m`,
`donchian_breakout: 1h`. **They are NOT registered** in `StrategyManager` / `load_sample_strategies`
(the live/active roster) — by design, since they failed validation. The config entry is harmless
routing metadata documenting their design TF.

## Tests
`tests/unit/test_replacement_candidates.py` (4/4 passing) — mechanism correctness only (not
profitability): each returns `None` on insufficient data; STR BUYs on a sharp down-extension in a
range; DCB BUYs on a channel break with volatility expansion.

## Auditability
Each signal is a single, explainable test (one z-score threshold; one channel-break + ATR gate) with
the decisive values recorded in the Signal `metadata` (z, regime flag, channel highs/lows, ATR). No
black-box components, no external/unavailable data.

## Integration status
**Not integrated into the active suite.** Per rule 12, because neither candidate cleared the READY bar,
the RETIRED slots remain empty. The implementation stands as the evidence trail for that decision and
is trivially removable (two new files + one config map entry) if desired.
