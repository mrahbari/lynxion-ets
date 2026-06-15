# Final Strategy Review (Phase 2) — Decision Gate

**Date:** 2026-06-12. Conducted only after Phase 1 (Operational Stabilization) completed
and the system was certified STABLE. Scope (allowed): Type-A/B defects, data-flow,
runtime, missing fields, broken adapters, incorrect calculations/indicator usage/
timeframe handling/execution wiring. **Not allowed:** new hypotheses/indicators/logic,
threshold or parameter optimization, curve fitting, Hyperopt.

## Method
Reviewed all 12 production strategies against the allowed defect classes, drawing on the
prior Strategy Fidelity Review, Rehabilitation, Timeframe Re-Architecture, Walk-Forward,
and the stabilization log analysis, plus a fresh adapter import/construction check.

## Findings

### Type-A/B defects already fixed (prior phases — verified still in place)
| strategy | defect | class | status |
|---|---|---|---|
| liquidity | swing levels missing `'type'` key → SELL-only | A (directional) | fixed |
| vwap_reversal | slope unit-bug (regime gate); `%24` simulated session | A (calc/data-flow) | fixed |
| scalping | absolute volume threshold vs data scale | A/B (data-flow) | fixed |
| mean_reversion | range window included tested bars | A (calc) | fixed |
| breakout/crypto_breakout | range recomputed each bar; range/threshold windowing | A (logic) | fixed |
| trend_following | trend-extreme gate effectively always-true | B (calc) | fixed |

### New lead reviewed this phase — NOT a defect
- **Direction-vs-Bias "Contradictory signal" warnings (~92×):** `strategy_adapters.py`
  `_determine_order_side` computes an order side from both `fused_signal.direction`
  (signed score) and `dominant_bias` (categorical). When they diverge it resolves
  deterministically (uses the stronger; bias if ≥1.5× direction strength, else direction)
  and logs the divergence. This is **intended conflict-resolution**, not an incorrect
  calculation or wiring defect. (Minor: the log level is WARNING for a normal handled
  condition — a C-class observability nit, out of A/B scope.)

### Adapter integrity check
All 12 strategy adapters **import and construct cleanly** (0 failures), and all execute
`generate_signal` error-free (per the signal-frequency diagnostic and the live production
run). **No broken adapters, no missing-field runtime defects.**

### Remaining Type-B items — out of Phase-2 allowed scope (documented, NOT changed)
Per `candidate-calibration-fixes.md`:
- **B-1 breakout `min_confidence` gate vs confidence scale** — remediation = changing a
  **threshold**, which Phase 2 explicitly **disallows** (threshold optimization). Left as
  documented; needs human review to decide if the confidence *formula* is a defect.
- **B-3 vwap_reversal dead `_check_rejection_pattern`** — remediation borders on
  **strategy redesign** (reinterpreting rejection geometry), disallowed. Left as documented.

## Decision Gate
- All fixable Type-A/B implementation/data-flow/runtime/adapter defects within scope are
  **resolved**.
- The only remaining items are (a) by-design behavior, (b) C-class observability, or
  (c) Type-B items whose remediation is **explicitly disallowed** in Phase 2 (threshold
  optimization / redesign).
- Therefore **no additional in-scope Type-A or Type-B defect remains**.

## Verdict: **STRATEGY SUITE FINALIZED**
The existing production strategy suite is **technically correct, stable, and fully
validated**. Implementation is sound; all in-scope defects are fixed. No further research,
edge discovery, or optimization is authorized.

**Honest assessment (unchanged, evidence-based):** technical correctness ≠ profitability.
The suite has **no demonstrated, persistent, cross-symbol, out-of-sample edge** and is
**NOT DEPLOYABLE with live capital** — READY 0 / NEEDS_IMPROVEMENT 11 / NON_VIABLE 1
(see rehabilitation, timeframe-validation, walk-forward, and readiness reports). The
project objective — "ensure the existing system is technically correct, stable, fully
validated, and honestly assessed" — is **met**. Work stops here per the decision gate.
