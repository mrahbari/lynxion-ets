# Phase 8 — vwap_reversal Rejection-Path Correctness Review

**Date:** 2026-06-12. Evidence-based ruling on whether the rejection-confirmation path is
dead code. No optimization, no tuning — ruling only.

## The mechanism
- **Entry** (`vwap_reversal_strategy_adapter.py`): BUY requires `price_deviation < −σ_band`
  (close meaningfully **below** session VWAP) **and** (`bullish_rejection` **or**
  `failure_swings`); SELL requires `price_deviation > +σ_band` (close **above** VWAP) and
  (`bearish_rejection` or `failure_swings`).
- **Rejection detector** (`_check_rejection_pattern`):
  - `bullish_rejection = (recent_lows[-1] < vwap) and (recent_closes[-1] > vwap)` — i.e. the
    latest bar **closes ABOVE VWAP** (a VWAP re-cross from below).
  - `bearish_rejection = (recent_highs[-1] > vwap) and (recent_closes[-1] < vwap)` — latest
    bar **closes BELOW VWAP**.
  - `failure_swings` — a 3-bar swing pattern, independent of VWAP side.

## The contradiction
- BUY needs `close < VWAP − band` (close **below** VWAP), but `bullish_rejection` needs
  `close > VWAP` (close **above** VWAP). **Mutually exclusive.**
- SELL needs `close > VWAP + band`, but `bearish_rejection` needs `close < VWAP`.
  **Mutually exclusive.**
So the `*_rejection` branch can never be the confirmation that admits an entry — only
`failure_swings` can.

## Empirical measurement (BTC, 20 000 1m bars; current σ-band code)
| | count |
|---|---|
| `bullish_rejection` fires (globally) | 36 |
| `bearish_rejection` fires (globally) | 40 |
| `failure_swings` fires (globally) | 467 |
| **`bullish_rejection` co-occurring with BUY zone (price < VWAP−band)** | **0** |
| `failure_swings` co-occurring with BUY zone | 36 |
| **`bearish_rejection` co-occurring with SELL zone (price > VWAP+band)** | **0** |
| `failure_swings` co-occurring with SELL zone | 90 |

The rejection detectors **do** evaluate True in isolation (36/40 times) — so they are not
trivially always-false — but they co-occur with the entry geometry **exactly 0 times**.

## Ruling
1. **Is the path genuinely dead code?** **Yes, in context.** It is reachable in isolation
   but **never simultaneously with the entry condition that gates it** (0/36 BUY-zone,
   0/40 SELL-zone). As a confirmation for an actual entry, it is dead.
2. **Reachable under realistic inputs?** **No** — not jointly with the deviation entry.
   `*_rejection` fires only when price is **at/crossing** VWAP; the entry fires only when
   price is **far from** VWAP. Disjoint by construction.
3. **Does the implementation match the documented hypothesis?** **No.** The hypothesis is
   reversion from a **deviation extreme**; correct confirmation would detect a reversal
   candle **at the extreme** (e.g. a wick rejection of the low/high), not a **VWAP
   re-cross**. `_check_rejection_pattern` was written for a "price-near-VWAP retest" setup,
   but is applied to a "price-far-from-VWAP reversion" entry — a geometry mismatch.

## Status & remediation (NOT performed)
The strategy is **not broken overall** — it still emits signals via the live
`failure_swings` path (observed: a SELL at confidence 0.656). The dead rejection branch
merely reduces signal frequency. Fixing it (redefining "rejection" at the deviation
extreme, using bar opens/wicks) **borders on redesign** of the confirmation logic, which
Phase 8 forbids. **Documented Type-B, not changed.**

## Disposition: **NEEDS_IMPROVEMENT**
Correct and functional (fires via failure_swings) with a documented dead-in-context
confirmation branch and a hypothesis–implementation geometry mismatch. Not READY (no edge:
Phase-7 WFO 0/0, ~12 trades at higher TF); not RETIRED (functions; defect is a bounded,
human-gated geometry correction, not structural impossibility).
