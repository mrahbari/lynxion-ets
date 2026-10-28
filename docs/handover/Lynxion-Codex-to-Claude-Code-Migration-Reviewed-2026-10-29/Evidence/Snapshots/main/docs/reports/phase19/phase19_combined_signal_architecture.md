# Phase 19 — Funding + Microstructure Combined Signal: Architecture & Method

**Date:** 2026-06-13. Analysis only. No existing strategy/parameter/threshold/risk/execution modified; no
profitability assumed; Phases 1–18 not overwritten. Documents the combined-signal design; results in the
companion files and `phase19_final_verdict.md`.

## Question

Two prior phases each surfaced a *weak* thread that, alone, was not deployable:
- **Phase 14 (funding):** extreme-negative funding → mild positive 24–72h forward return on BTC/ETH
  (WEAK, fails SOL, walk-forward-fragile).
- **Phase 17 (microstructure):** order-flow aggressor imbalance carries little incremental info; the
  *funding × flow* capitulation cell (extreme-neg funding + aggressive selling) gave +0.011% — real,
  cross-symbol-consistent, but ~37× below cost at a 30-min horizon.

Phase 19 asks: **does combining them produce a deployable, stable, cross-symbol edge that neither
component does?** The natural synthesis — use the *slow* funding signal to define the regime and *fast*
microstructure flow to confirm/time entry, evaluated at funding's native 24–72h horizon (where the move
can exceed the 0.30% cost).

## Data

- **Funding:** `data/history/raw/funding/<SYM>-USDT.csv` (8h cadence, Phase-14 dataset).
- **Microstructure:** `data/history/micro/5m/<SYM>-USDT.csv` (Phase-17 futures layer: aggressor
  imbalance from taker-buy volume + trade-intensity), BTC/ETH/SOL, 2024-06 → 2026-06.
- **Sampling:** evaluation points = funding update times (8h, matching Phase-14 sampling) inside the
  microstructure window → ~2,218 funding events/symbol. At each, microstructure features are read from
  the 5m bars up to that instant; forward returns at 4/12/24/72h from 5m closes.

## A-priori signals (NOT tuned)

Per funding event, with funding regime from the symbol's own distribution (extreme_neg ≤ p10,
extreme_pos ≥ p90) and `flow_k` = mean 5m aggressor imbalance over the prior hour (K=12 bars),
`intensity_z` = trade-count z-score:

**Components (baselines):**
- `funding_only_extneg_long` — extreme-neg → long
- `funding_only_extpos_short` — extreme-pos → short
- `flow_only_contrarian` — sell-flow → long / buy-flow → short (no funding)

**Combined (the phase's hypotheses):**
- `COMBO_capitulation` — extreme-neg funding **and** sell-flow → long (capitulation reversal)
- `COMBO_exhaustion` — extreme-pos funding **and** buy-flow → short (crowded-long exhaustion)
- `COMBO_capit+liqexp` — capitulation **and** liquidity expansion (`intensity_z` > 0) → long

All thresholds are a-priori percentiles / signs; nothing optimised.

## Evaluation contract (carried from prior phases)

- **Per-symbol** BTC/ETH/SOL; **cost-adjusted** net forward-return per signal (round-trip **0.30%**,
  unchanged); **4-fold walk-forward** (sign stability); **cross-symbol** robustness.
- **Incremental test:** combined signal vs each standalone component — does microstructure confirmation
  *add* deployable value over funding-only / flow-only?
- **Honest sampling caveat:** funding events are 8h-spaced but horizons run to 72h → overlapping forward
  windows + funding-block autocorrelation make the *effective* sample far below nominal n. WFO +
  cross-symbol are the robustness arbiters, not nominal n or a single window's mean.

Results → `funding_microstructure_interaction.md`; walk-forward/cross-symbol → `combined_walkforward_validation.md`;
verdict → `phase19_final_verdict.md`. Harness: `scripts/phase19_funding_micro_combined.py`. Raw:
`phase19_results.json`.
