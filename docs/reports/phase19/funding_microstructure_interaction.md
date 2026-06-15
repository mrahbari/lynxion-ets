# Phase 19 — Funding × Microstructure Interaction Results

**Date:** 2026-06-13. Analysis only; no strategy/parameter/threshold/risk/execution changes; no
profitability claim. Net forward-return per signal, **net of 0.30% round-trip cost**, per-symbol,
~2,218 funding events/symbol (2024-06 → 2026-06). Focus on funding's native horizons (24h, 72h).

## Capitulation: extreme-neg funding + sell-flow → long (the headline combination)

| Horizon | Signal | BTC | ETH | SOL |
|---|---|---:|---:|---:|
| 24h | funding-only extneg→long | +0.049% | +0.290% | −0.605% |
| 24h | **COMBO capitulation** | **+0.072%** | +0.213% | −0.790% |
| 72h | funding-only extneg→long | +0.519% | **+0.815%** | −0.966% |
| 72h | **COMBO capitulation** | **+0.635%** | +0.404% | −1.146% |

- **Positive and cost-surviving on BTC and ETH** at 24–72h (BTC combo +0.64% @72h, win 0.59; ETH +0.40%,
  win 0.50) — theory-aligned capitulation bounce.
- **Decisively negative on SOL** (−0.79% @24h, −1.15% @72h, win 0.43–0.45). The effect **fails
  cross-symbol** — exactly the BTC/ETH-yes, SOL-no pattern Phase 14 already flagged for funding.

## Does microstructure confirmation BEAT funding-only? (the core validation question)

Combination minus funding-only component, at 72h:

| Symbol | funding-only | COMBO capitulation | Δ from adding flow |
|---|---:|---:|---:|
| BTC | +0.519% | +0.635% | **+0.116%** (flow helps) |
| ETH | +0.815% | +0.404% | **−0.411%** (flow HURTS) |
| SOL | −0.966% | −1.146% | **−0.180%** (flow hurts) |

- **Flow confirmation does not reliably add value.** It marginally helps BTC, but *hurts* ETH (cuts the
  funding-only edge nearly in half) and SOL. On net across symbols, the microstructure filter **subtracts**
  more than it adds — it mostly reduces sample and injects noise.
- The combination's positive cells (BTC/ETH) are **inherited from the funding component (Phase 14)**, not
  *created* by microstructure. The phase's central premise — that combining the two weak signals yields
  something better — is **not supported.**

## Exhaustion: extreme-pos funding + buy-flow → short

| Horizon | Signal | BTC | ETH | SOL |
|---|---|---:|---:|---:|
| 72h | funding-only extpos→short | −0.351% | −0.408% | −0.270% |
| 72h | **COMBO exhaustion** | −0.495% | −0.649% | −0.362% |

- **Negative on all three** (the short loses): extreme-positive funding does **not** predict reversal,
  and buy-flow confirmation makes it worse. Consistent with Phase 14 (extreme_pos carried no contrarian
  signal). No edge.

## Flow-only (no funding)

Contrarian flow alone: −0.28% to −0.41% net on all three symbols, win 0.48–0.51, 0–1/4 folds → **no edge
without funding** (consistent with Phase 17).

## Liquidity-expansion filter (capitulation + intensity_z>0)

Adding a liquidity-expansion requirement sharpens **BTC** (24h net +0.167%, all available folds positive
— but n=64) yet **destroys ETH** (72h flips to −0.359%) and stays negative on SOL. A BTC-only, tiny-sample
improvement — not cross-symbol robust.

## Reading

The combination reproduces the **same weak, BTC/ETH-only, SOL-failing funding thread** from Phase 14;
microstructure confirmation does not convert it into a cross-symbol edge and on balance degrades it.
Walk-forward stability and the final classification → `combined_walkforward_validation.md`,
`phase19_final_verdict.md`.
