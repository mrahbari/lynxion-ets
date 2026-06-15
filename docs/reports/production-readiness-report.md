# Production Readiness Report

**Date:** 2026-06-12. **Scope:** the 12 fixed production strategies after Strategy
Rehabilitation. **Bottom line:** **NOT PRODUCTION-READY. Do not deploy any strategy with
live capital.** 0 READY · 11 NEEDS_IMPROVEMENT · 1 NON_VIABLE.

## Verdict
No strategy demonstrates **positive, stable, sufficiently-sampled expectancy**. The
rehabilitation made the suite **correct and measurable** (every Type-A defect removed; all
12 run their real logic), but correctness is not profitability — and the READY bar
requires profitability evidence. Therefore none is deployable.

## Why (two independent, evidence-based reasons)

1. **The configured evaluation timeframe (1m) is structurally cost-incompatible.**
   Round-trip cost is 0.30% (fee 0.10%×2 + slippage 0.05%×2); 1m take-profit geometry
   (2.25×ATR ≈ 0.10%) is ~3× *smaller*. Every strategy posted a 2–5% net win rate on 1m
   — a cost artifact, not a signal verdict. Cost-breakeven ≈ **15m**.
2. **Even on a cost-viable timeframe (1h), there is no stable cross-symbol edge.** Win
   rates normalize to ~20% and a few cells turn positive (some GO), but **no strategy is
   positive across BTC, ETH and SOL** — the BTC/ETH winners are destroyed on SOL. This is
   consistent with the Phase-5 finding of no gross entry edge on OHLCV.

## Deployment recommendation
**Deploy nothing now.** Concrete prerequisites before any strategy could be reconsidered:

1. **Re-baseline on the cost-viable timeframe (≥15m, recommend 1h).** 1m is the wrong
   substrate for these ATR-geometry strategies. The `BACKTEST_TIMEFRAME` hook +
   `higher_tf_eval.py` already enable this; `eval_matrix_1h.json` is the first such
   baseline. **This is the #1 action** — it is a data/configuration correction, not a
   strategy change. *(Decision flag: this presumes the production target timeframe is
   ≥15m; if the mandate is genuinely 1m-only, the entire suite is NON_VIABLE-on-1m.)*
2. **Require cross-symbol AND cross-window stability**, not single-cell positives, before
   any READY claim. SOL is currently a universal failure mode — any candidate must survive
   it.
3. **Resolve the oi_footprint data dependency** (real open-interest feed) before judging
   its named edge; it currently uses a volume×1.5 proxy.
4. **Walk-forward / out-of-sample validation** on the chosen timeframe before live capital
   (current evidence is in-sample backtest only).
5. **Do not pursue profitability via Type-B threshold tuning** — that is curve-fitting and
   will not create genuine edge (see `candidate-calibration-fixes.md`).

## Risk statement
Deploying any current strategy on 1m would lose to transaction costs by construction.
Even on a viable timeframe, the absence of stable cross-symbol edge means expected live
PnL is negative after costs. No configuration found in this rehabilitation is deployable.

## What the rehabilitation *did* achieve
- Removed all Type-A defects (liquidity directional bug; vwap_reversal & scalping
  data-flow bugs) — the suite is now correct and measurable.
- Established the **dominant constraint** (timeframe/cost) with quantified evidence and an
  empirical cross-timeframe re-run — converting "the strategies lose" into the actionable
  "the strategies are mistimed *and* lack stable edge."
- Produced reproducible matrices (1m, 15m, 1h) and a Type-B register that prevents
  accidental curve-fitting.

See `strategy-rehabilitation.md`, `strategy-readiness-matrix.md`, `final-strategy-roadmap.md`,
`candidate-calibration-fixes.md`, `hypothesis-fidelity-review.md`.
