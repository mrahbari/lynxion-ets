# Phase 6 · Step 8 — Regime-Conditional Hypotheses (vol-gated, 24-symbol)

_Last free-data class (blueprint §3B). Reversion gated to high-vol bars, momentum to low-vol bars (signal=NaN outside regime → IC on in-regime bars only). 24 symbols, multi-year 8h, trailing-vol regime (lookahead-safe). Horizons [1, 3, 9]. **Cumulative** family = 1047, BH-FDR, default REJECT. Signal quality only._

## Breadth

| hypothesis | overall | best horizon | mean IC (in-regime) | same-sign & sig | promoted |
|---|---|---:|---:|---|---:|
| revert_highvol_3 | **PROVISIONAL** | 1 | +0.064 | 17/24 | 2/24 |
| revert_highvol_9 | **ARCHIVE** | 3 | +0.049 | 5/24 | 0/24 |
| momentum_lowvol_9 | **ARCHIVE** | 9 | -0.036 | 3/24 | 0/24 |
| momentum_lowvol_30 | **ARCHIVE** | 9 | -0.054 | 6/24 | 0/24 |

**PROMOTE: 0** — none
**PROVISIONAL: 1** — revert_highvol_3
**ARCHIVE: 3**

## First breadth-backed lead in the whole Phase-6 search

**`revert_highvol_3` — short-horizon reversion in high-volatility regimes — is the
strongest, most generalisable signal found.** Mean in-regime IC **+0.064** at the
8h forward horizon, with **17/24 symbols same-sign-and-significant** (every prior
batch had only 1–3/24). It is **PROVISIONAL**, not promoted: the strict per-symbol
gate (monotonicity/OOS/block) under the conservative **cumulative 1047-test family**
fully promoted only 2/24 — but the cross-symbol *breadth* is real and economically
sensible (short-term overreactions mean-revert during high-vol/panic). The longer-
horizon variant (`revert_highvol_9`, +0.049, 5/24) is directionally consistent but
weaker; low-vol momentum is null/negative.

**This is a candidate, not a result.** Required before any reliance, in order:
1. **True out-of-sample confirmation** on a held-out later period (the regime idea
   is a pre-registered §3B class, so lower snoop risk than an in-sample-derived
   lead — but OOS is still mandatory).
2. **Execution/cost reality** — recall Phase-5: a ~10 bps cost on tight stops
   eats ~0.6R/trade. An IC of +0.064 is small; it must clear costs in the existing
   execution/edge-gate stack before it means profit. Signal-level edge ≠ tradeable
   edge.

_No tuning, no execution simulation here — signal quality only._
