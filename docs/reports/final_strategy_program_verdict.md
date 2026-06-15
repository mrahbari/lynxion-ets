# Final Strategy Program Verdict

**Date:** 2026-06-13
**Question:** Can the strategy suite be improved by replacing the two RETIRED strategies with
better-designed alternatives?

# Verdict: ⛔ NO replacement is justified. The two RETIRED slots remain EMPTY.

Per rule 12: no candidate outperformed the retired strategies, so the slots stay empty and this report
states so explicitly. Evidence — not assumption — determined the outcome.

---

## What was done (full program, evidence-driven)
1. **Candidate study** (`strategy_candidate_study.md`): 5 candidates studied against hypothesis clarity,
   architecture compatibility, data availability, non-duplication, and auditability. Rejected 3
   (cross-sectional RS = architecture-incompatible; Bollinger reversion = duplicate; time-of-day =
   curve-fitting risk). Selected 2 distinct, a-priori, OHLCV-only candidates: **Short-Term Statistical
   Reversal (STR)** and **Donchian Channel Breakout (DCB)**.
2. **Implementation** (`new_strategy_implementation.md`): both built as `BaseStrategyAdapter` subclasses
   with a-priori parameters, config routing, and 4 passing mechanism tests. No existing strategy/param/
   threshold modified.
3. **Validation** (`new_strategy_validation.md`): design-TF + per-symbol + regime-conditioned +
   cross-period + 4-fold walk-forward, net of 0.30% round-trip cost.

## Outcome
| Candidate | In-regime expectancy (BTC/ETH/SOL) | Walk-forward | Verdict |
|---|---|---|---|
| STR | −0.33% / −0.30% / −0.44% | 0/4 all symbols | **INVALIDATED** |
| DCB | −0.25% / −0.14% / −0.38% | 0–1/4 | **INVALIDATED** |

Both are well-powered (322–546 in-regime signals/symbol), stable-negative net of cost, and fail
walk-forward — the same edgeless pattern as the entire existing suite.

## Updated suite state
- READY = 0 (unchanged)
- NEEDS_IMPROVEMENT = 5 (unchanged: breakout, liquidity, volatility_breakout, mean_reversion, vwap_reversal)
- INVALIDATED = 5 (unchanged: trend_following, momentum, mtf_trend, oi_footprint, sweep_scalper)
- RETIRED = 2 **slots EMPTY** (scalping, crypto_breakout removed; **no replacement deployed**)
- Candidate strategies STR, DCB: **INVALIDATED, not deployed** (implemented + evaluated only)

## Why this is the honest result
The deployment-validation program had already shown that the full existing suite, correctly deployed,
has no positive cross-period-stable edge net of cost on BTC/ETH/SOL. The two new candidates were
genuinely distinct, a-priori (un-tuned), and well-powered — and they reproduced the same net-negative
result. This is consistent, well-evidenced confirmation that **OHLCV-only directional strategies on
these assets do not clear the cost hurdle (~0.30% round-trip) under the available data and the no-tuning
constraint** — not a failure of any single design.

## Recommendation (no action taken — analysis only beyond the rejected candidates)
- Keep the RETIRED slots **empty**. Adding net-negative strategies would only add cost and risk.
- A genuinely *new* edge would likely require inputs the architecture currently lacks (reliable
  order-book/microstructure, funding, sufficient open-interest, or cross-asset/portfolio logic) and/or
  a relaxation of the no-tuning constraint — both **out of scope** here and neither assumed to succeed.
- The implemented candidates remain in the tree as a documented, reproducible negative result; they are
  trivially removable and are **not** wired into the active suite.

## Scope / honesty caveats
- The validation metric is a directional signal-quality-with-cost proxy (forward-return net of cost),
  not a path-dependent SL/TP backtest — consistent with how the existing suite was re-evaluated, so the
  comparison is apples-to-apples.
- No profitability was assumed at any step; every classification rests on the measured evidence.
- No existing strategy logic, parameters, or thresholds were changed; infrastructure remained frozen.

**Bottom line:** the strategy suite **cannot** be improved by replacing the RETIRED strategies with
these (or, by extension, similar OHLCV-only) alternatives. The slots stay empty.
