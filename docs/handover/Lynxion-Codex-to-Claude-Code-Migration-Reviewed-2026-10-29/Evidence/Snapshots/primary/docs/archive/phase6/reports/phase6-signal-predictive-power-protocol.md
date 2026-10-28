# Phase 6 · Work Item 1a — Signal Predictive-Power Measurement Protocol

**Date:** 2026-06-11   **Type:** methodology specification (no implementation).
Defines *how* a candidate signal's raw predictive edge is measured — the test
Phase 5 could not run. No code, no backtests, no strategy edits here.
Parent: `docs/reports/phase6/PHASE6-BLUEPRINT.md`.

## 0. Why this exists

Phase 5 proved the deficit is in **signal generation** (gross-negative entry
edge), and that the backtester *conflates* signal + SL/TP geometry + cost, so it
cannot answer "does this signal predict forward returns at all?" This protocol
measures **signal → forward-return** relationship in isolation, *before* any
geometry/sizing/cost. A signal must earn an edge here before it is ever wrapped
into a strategy.

## 1. Unit of analysis

A **signal** = a bar-aligned time series `s(t)` per (symbol, timeframe), either:
- **continuous** — a predictive score (higher ⇒ more bullish), or
- **event** — a sparse boolean/categorical flag.

Each signal is registered with: definition, hypothesis class (blueprint §3A),
look-back window, and the exact information set available at time `t`.

## 2. Forward-return labels (no lookahead — CLAUDE.md #1/#2/#3)

- Decision is taken on **closed** bar `t`; the forward return uses prices strictly
  **after** `t` (enter at `t+1` open). Signal features must use only data ≤ `t`.
- Compute forward log-returns over a **horizon grid** `h ∈ {1, 5, 15, 60, 240,
  1440} bars` (and their time equivalents). Multiple horizons are mandatory — the
  E-P5.3 MFE evidence (mean ~0.3–0.5R) suggests the current entries may simply be
  measured at the wrong horizon.
- Both **directional** (sign) and **magnitude** labels retained.
- Volatility-normalise returns (divide by rolling realised vol) so IC is
  comparable across symbols/regimes.

## 3. Predictive-power metrics (per signal × horizon)

1. **Information Coefficient (IC):** Spearman rank corr between `s(t)` and forward
   return. Report IC and its **t-stat with Newey–West/HAC correction** (overlapping
   forward windows induce serial correlation — naïve t-stats overstate
   significance).
2. **IC-decay curve** across the horizon grid → locate where (if anywhere) edge
   lives.
3. **Quantile/decile spread:** bucket `s(t)` into deciles; measure monotonicity and
   top-minus-bottom forward-return spread + t-stat. Monotonic spread is stronger
   evidence than a single IC point.
4. **Directional hit-rate** for sign-based use.
5. **Event signals:** event-study cumulative abnormal return (CAR) vs a matched
   baseline, with confidence band.

## 4. Out-of-sample design (leakage-proof — CLAUDE.md #16/#17)

- **Time-ordered split:** train / validation / **locked holdout**. Holdout is
  touched exactly once, at the very end, per signal family.
- **Purged + embargoed walk-forward / combinatorial CV** (López de Prado): purge
  training labels overlapping the test window; embargo a gap so the overlapping
  forward horizon cannot leak.
- **Cross-symbol generalisation:** an edge must hold across BTC/ETH/SOL (not curve-
  fit to one). Report IC per symbol.
- **Regime conditioning:** report IC within volatility/liquidity/trend regimes
  (blueprint §3B) — a signal valid only in a regime is acceptable *if* the regime
  is identifiable out-of-sample.
- **Stability:** rolling-window IC; reject signals whose edge is non-stationary.

## 5. Multiple-testing discipline (anti-snooping — CLAUDE.md #4)

Discovery tests many hypotheses ⇒ false positives are the dominant risk.
- **Pre-register** every signal tested and the total count `N` before looking at
  results.
- Control family-wise error / FDR: **Benjamini–Hochberg** on IC p-values, and/or
  **Deflated Sharpe Ratio** for any strategy-level metric, both as a function of
  `N`.
- **Default verdict = REJECT.** A signal is promoted only on surviving correction.

## 6. Promotion gate (signal → strategy)

A signal is **promoted** to the (reused) execution/edge-gate stack only if, on the
**holdout**, it shows: significant HAC IC after multiple-testing correction at a
useful horizon, a monotonic decile spread, consistency across ≥2 symbols, and
stable rolling IC. Otherwise it is archived with its measured (non-)edge.

**Strict decoupling:** this layer has **no SL/TP, no sizing, no costs**. Geometry,
risk, and execution realism are a *separate, later* concern handled by the
existing Phase-5 infrastructure — which is now trustworthy and is **reused, not
rebuilt**, as the downstream validator.

## 7. Reuse vs build

- **Reuse (Phase-5 assets):** history loaders, the regime classifier (as a
  *conditioning variable* only — E-P5.4 showed it is not a standalone trigger), the
  realistic backtester + edge-gate as the **downstream** validator for promoted
  signals.
- **Build (new):** the predictive-power harness itself (forward-label generator,
  IC/decile/event-study engine, purged-CV splitter, multiple-testing controller,
  signal registry). This does not exist today.

## 8. Outputs (per signal)

IC table (× horizon × symbol), IC-decay curve, decile-spread + t-stats, regime-
conditional IC, rolling-IC stability, multiple-testing-corrected verdict
(PROMOTE / ARCHIVE), and a pre-registration record. These become the Phase-6
analogue of the Phase-5 blocker ledger — an **edge ledger of tested hypotheses**.

## 9. Explicit non-goals (guardrails)

No parameter tuning, no SL/TP optimisation, no re-running Phase-5 strategy
backtests, no strategy-logic edits. This protocol *measures*; it does not *fit*.
Implementation of the harness is a **separate, later** work item, only on
authorization.
