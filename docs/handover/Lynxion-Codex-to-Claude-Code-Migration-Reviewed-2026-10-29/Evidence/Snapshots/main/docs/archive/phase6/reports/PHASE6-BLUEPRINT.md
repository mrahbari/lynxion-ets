# Phase 6 — Edge Discovery System: Initiation Blueprint

**Date:** 2026-06-11   **Type:** definition only — NOT an optimization plan.
No fixes to existing strategies, no parameter tuning, no backtests. This document
defines *what Phase 6 is* and *where to look*, not how to build it.

Predecessor: Phase 5 (diagnostics) is officially complete; verdict **NOT READY
(no demonstrable edge)** accepted. See `docs/reports/phase5/PHASE5-SYNTHESIS.md`.

---

## 1. Phase 5 conclusion — one statement (what was PROVEN, not suspected)

> **On the tested universe (1 year of 1-minute OHLCV for BTC/ETH/SOL, 90/180/365-day
> windows, long side), with the two catastrophic execution bugs corrected, every one
> of the 11 evaluable strategies has NEGATIVE GROSS expectancy — they lose even with
> perfect, cost-free, bug-free execution. Therefore the profitability deficit is
> definitively located in SIGNAL GENERATION (absent realized directional entry edge),
> and is NOT caused by execution, fees/slippage, MTF alignment, trade management, or
> portfolio construction.**

What this rules out *as proven, not suspected*: cost-masking (gross<0 underneath
all costs), execution-bug-masking (B1/B2 fixed), MTF-conflict (refuted: a HTF gate
*worsens* expectancy), and trade-management starvation (overlays cannot rescue
gross-negative trades). The one bounded, unproven residual — whether latent entry
edge is *suppressed by adverse SL/TP geometry* — is exactly what Phase 6's
methodology is designed to settle.

---

## 2. Phase 6 objective — from "no edge exists" to "edge-discovery system"

**Change the unit of work from "strategy" to "signal hypothesis with measured
information content."**

Phase 5 validated *predefined* strategies and found none with edge. Phase 6 must
instead **systematically generate, measure, and rank candidate entry signals by
predictive power — before any of them is wrapped in SL/TP, sizing, or execution
logic.** Concretely, Phase 6 builds a discovery loop that:

1. proposes signal hypotheses (from explicit hypothesis classes, §3A),
2. measures each signal's raw forward-return predictive power **independent of
   geometry/cost** (the test Phase 5 could not run),
3. subjects survivors to strict out-of-sample / multiple-testing-corrected
   validation,
4. only then promotes a signal into the existing (now-trustworthy) execution +
   edge-gate stack for realistic evaluation.

Success criterion for Phase 6 = **discovery of one or more signals with
statistically significant, out-of-sample, multiple-testing-corrected predictive
edge** — not improved metrics on the existing twelve.

---

## 3. Top-level research directions (NO implementation)

### A. New signal hypothesis classes (beyond single-asset indicator/pattern rules)
- **Cross-sectional / relative-value:** lead-lag and spread dynamics across the
  ~0.83-correlated majors (BTC↔ETH↔SOL); market-neutral framing instead of
  independent directional longs.
- **Statistical structure:** cointegration / mean-reversion at deliberately chosen
  horizons (current entries showed tiny MFE ⇒ wrong horizon is plausible).
- **Order-flow / microstructure edges** (data-dependent — §3C): imbalance,
  absorption, sweep/liquidation cascades, real OI/funding — the *named* edges the
  current micro strategies could never actually compute.
- **Regime-conditional signals:** momentum/reversion that is only expressed inside
  specific volatility/liquidity/trend states (rather than always-on).
- **Carry / derivatives-positioning:** funding-rate carry, basis, liquidation
  pressure, options-implied skew.

### B. Market-regime decomposition beyond current features
- The current regime label (single-timeframe trending_up/down/ranging) was shown
  *non-informative* for outcomes (E-P5.4). Replace with richer state estimation:
  **volatility regimes** (realized-vol clustering, vol-of-vol), **liquidity
  regimes**, **multi-timeframe state-space / HMM / change-point detection**, and
  **cross-asset risk-on/off** regimes — each as a *conditioning variable* for §3A
  signals, not a standalone trade trigger.

### C. Alternative data & structural market assumptions
- **Acquire what the system lacks:** L2 order book, trade tape, open interest,
  funding, liquidations (resolves the B12 data gap), plus on-chain/exchange flows.
- **Multi-resolution:** the system is 1m-OHLCV-only; discovery needs multiple
  native resolutions, not resampling.
- **Revisit structural assumptions:** majors are ~0.83 correlated and the suite is
  long-only — Phase 6 should treat the universe as a *small set of correlated
  bets* (favouring cross-sectional / market-neutral / both-sided structure) rather
  than many independent directional longs.

### D. Entry-signal discovery methodology
- **Predictive-power first:** measure each signal's information coefficient /
  forward-return relationship *before* any backtest; reject zero-IC signals at the
  gate.
- **Out-of-sample by construction:** walk-forward and **purged/combinatorial
  cross-validation** from day one.
- **Multiple-testing discipline:** because discovery tests many hypotheses,
  mandate deflated-Sharpe / FDR control to prevent data snooping (CLAUDE.md
  standard #4). This is the single biggest risk of an edge-discovery program.
- **Decouple edge research from execution research:** a signal earns promotion on
  predictive power alone; geometry/sizing/cost are a *separate, later* layer
  (reusing Phase-5 infrastructure).

---

## 4. What CANNOT be fixed vs what MUST be rebuilt

### Cannot be solved by improving the current system (proven dead ends for profitability)
- **Adding/refining SL/TP geometry, trailing, breakeven, partials (B7/B8/B16),
  MTF gating (B9), portfolio/heat controls (B10), cost reduction, or parameter
  tuning of the 12 strategies.** All operate *downstream* of signal generation;
  none can create directional predictive power that the gross-negative result
  proves is absent. These remain valuable as **risk/cost controls for a signal
  that already has edge** — never as a source of edge.
- **The existing 12 strategies as profitability candidates.** Optimizing them is
  out of scope and cannot reach breakeven (gross < 0 for all).

### Must be (re)built — and what to KEEP
- **REBUILD: the signal/hypothesis layer.** Replace hand-coded indicator strategies
  with a hypothesis-driven discovery process (§3A–D).
- **BUILD NEW: a signal-research harness** that measures raw forward-return
  predictive power independent of execution — this does not exist today (the
  backtester conflates signal + geometry + cost).
- **BUILD NEW / ACQUIRE: the data foundation** — microstructure + alternative +
  multi-resolution data (§3C).
- **KEEP / REUSE (do NOT rebuild): the execution, realistic-fill, risk, edge-gate,
  and reporting infrastructure.** Phase 5's real achievement is that this stack is
  now *trustworthy and bug-free*. It becomes the **validation backend** for
  discovered signals. Phase 6 swaps the signal *source*, not the plumbing.

---

## 5. Scope guardrails for Phase 6 initiation

- This is a **blueprint**, not an implementation or optimization plan.
- No fixes to existing strategies; no tuning; no re-running of Phase-5 backtests.
- First concrete Phase-6 work item (when authorized) = define the **signal-
  predictive-power measurement protocol** (§3D) and the data-acquisition decision
  (§3C) — both are *research-methodology* tasks, not strategy edits.

> Reproducibility: the Phase-5 method and findings of record are version-controlled
> — tooling in `research/profitability_diagnostics/`, reports in `docs/reports/phase5/`, data in
> `data/results_storage/` (CLAUDE.md #18). This blueprint lives in
> `docs/reports/phase6/`.
