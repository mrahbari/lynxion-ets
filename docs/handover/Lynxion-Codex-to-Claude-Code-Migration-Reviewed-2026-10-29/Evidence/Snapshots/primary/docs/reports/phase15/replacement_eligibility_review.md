# Phase 15 — Replacement Eligibility Review (RETIRED slots)

**Date:** 2026-06-13. Analysis only; no strategy created or modified. Assesses whether the **2 RETIRED
slots** (scalping, crypto_breakout) may be filled. Per the phase mandate, replacement is authorized
**ONLY IF ALL FIVE** conditions hold; otherwise the slots stay empty.

## The five gating conditions — assessed against evidence

| # | Condition | Finding | Met? |
|---|---|---|---|
| 1 | A genuine **architectural gap** is identified | The suite already spans trend, momentum, mean-reversion, breakout, VWAP, liquidity, scalping, OI-footprint, MTF. The only *information* gaps (funding, CVD, OI) are data/feature gaps, not strategy-archetype gaps — and adding them = building a **new strategy** on data the decision path doesn't consume. No missing *archetype*. | **NO** (no archetype gap; arguable feature gap only) |
| 2 | **No existing strategy covers** that gap | Every directional/mean-reversion/breakout archetype is already present (and INVALIDATED/INCONCLUSIVE). A contrarian-positioning idea overlaps mean_reversion's role. | **NO** |
| 3 | Candidate **materially different** from all existing | The prior replacement program (E11) already built the two most materially-different OHLCV candidates — `short_term_reversal`, `donchian_breakout` — both **INVALIDATED** (stable-negative net of cost, WFO 0–1/4). The only *genuinely* different lever is funding-based, but see #5. | partial |
| 4 | Implementable with **data already in the repo** | Funding (3y×24sym) and OI (~30d) are on disk → technically yes for a funding/OI idea. | YES (data exists) |
| 5 | Validation **demonstrates superiority over the retired slots** | **This is the decisive failure.** No candidate demonstrates a positive, cost-adjusted, walk-forward-stable edge: (a) the 2 E11 candidates are INVALIDATED; (b) Phase-15 shows every re-tested strategy negative; (c) the strongest data lead, **funding** (Phase-14), was classed **WEAK_INFORMATION** — single-regime (extreme-negative), works on BTC/ETH but **fails on SOL**, magnitude-unstable, and explicitly **not** shown to survive cost. An **empty slot (0 PnL, 0 risk) strictly dominates any candidate not proven net-positive.** | **NO** |

## Why an empty slot wins

A RETIRED slot contributes zero return and zero risk. To justify filling it, a candidate must be shown
**net-positive after cost and stable out-of-sample** — i.e. strictly better than zero. Across the entire
program **nothing meets that bar**:

- OHLCV archetypes: INVALIDATED or INCONCLUSIVE (Phase-15).
- Purpose-built replacement candidates (E11): INVALIDATED.
- Open Interest (oi_footprint): DIRECTIONAL_NO_GO; long-history OI untestable (~30d cap).
- Funding (Phase-14): WEAK_INFORMATION only; not standalone-viable; cost-survival not demonstrated;
  building it would be creating a new strategy on a signal the prior phase said **not to assume**.

Filling a slot with any of these would inject a **known-or-unproven-losing** strategy in place of a
guaranteed-neutral empty slot — a strict regression in expected risk-adjusted outcome.

## Decision

**Conditions 1, 2, and 5 are NOT met → REPLACEMENT DENIED. Both RETIRED slots remain EMPTY.**

This is consistent with the prior replacement program (which also retained empty slots after both
candidates invalidated) and with the mandate's fallback: *"If these conditions are not met, keep RETIRED
slots empty."* The single thread worth any future attention — extreme-negative-funding contrarian context
on BTC/ETH (Phase-14, WEAK) — is a research lead, **not** a validated replacement, and pursuing it would
require an un-frozen strategy-build phase plus a cost-survival demonstration it has not passed.
