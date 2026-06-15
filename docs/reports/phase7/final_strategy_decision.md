# Phase 7 — Final Strategy Decision

**Date:** 2026-06-12. Evidence-based final disposition for every one of the 12 production
strategies. Dispositions: **READY** (profitable + stable + statistically supported) ·
**NEEDS_IMPROVEMENT** (correct + measurable, no stable edge, non-tuning path exists) ·
**NON_VIABLE** (structural market/timeframe incompatibility) · **RETIRED** (overwhelming
non-viability or redundant — removed from the go-forward suite).

Basis: `strategy_deep_review.md`, `strategy_issue_registry.md`, `strategy_survivor_ranking.md`,
`production_subset_candidates.md`, and the matrix/WFO evidence (324 + 144 cells).

## Final dispositions

| strategy | disposition | decisive evidence |
|---|---|---|
| trend_following | **NEEDS_IMPROVEMENT** | correct; all-symbol-negative; WFO 2/4 (coin-flip), no persistence |
| mean_reversion | **NEEDS_IMPROVEMENT** | correct; only 6 trades at higher TF (intrinsic selectivity) — unjudgeable, not non-viable |
| momentum | **NEEDS_IMPROVEMENT** | correct; BTC-only positive, SOL −3364; WFO 2/4 |
| breakout | **NEEDS_IMPROVEMENT** | untradeable as wired (B1 confidence-vs-`min_confidence`); needs a human correctness ruling (not autonomous tuning) |
| liquidity | **NEEDS_IMPROVEMENT** | Type-A fixed (directional restored); ETH-only small positive; no stable edge |
| mtf_trend | **NEEDS_IMPROVEMENT** | correct (single-TF EMA proxy); BTC-only marginal, ETH/SOL deeply negative |
| oi_footprint | **NEEDS_IMPROVEMENT** | best cell (ETH +405, GO) but **data-blocked** (volume OI proxy); fails cross-symbol/WFO |
| sweep_scalper | **NEEDS_IMPROVEMENT** | thin sample (225 trades); no stable edge, not enough to declare non-viable |
| vwap_reversal | **NEEDS_IMPROVEMENT** | Type-A fixed; Type-B residual (dead rejection); 12 trades at higher TF |
| volatility_breakout | **NEEDS_IMPROVEMENT** | correct; small negatives, no positive cell; no edge |
| **scalping** | **RETIRED** | structural cost-incompatibility (Type-C): negative on **every** timeframe **and** symbol; thesis (move>cost) unmet at any tradeable frequency. Overwhelming non-viability. |
| **crypto_breakout** | **RETIRED** | explicit code **alias** of `breakout` (identical logic/config/results) — not a distinct strategy; redundant. |

**Tally: READY 0 · NEEDS_IMPROVEMENT 10 · NON_VIABLE 0 · RETIRED 2.**

## Rationale for the disposition split
- **0 READY:** the READY bar requires profitability evidence; the walk-forward test found
  **no temporally-stable, cross-symbol edge** in any strategy. Declaring any READY would
  be unsupported by evidence (and is explicitly forbidden).
- **10 NEEDS_IMPROVEMENT, not NON_VIABLE:** each is implementation-correct and measurable,
  and has a **non-tuning** improvement path (correct timeframe ≥15m, real-OI data,
  cross-symbol/WFO gating, or a human correctness ruling for breakout). Their failure is
  "no edge demonstrated yet," not proven structural impossibility — so NEEDS_IMPROVEMENT
  is the honest, conservative call.
- **2 RETIRED:** crypto_breakout is a literal duplicate (retiring it removes redundancy,
  not capability); scalping has overwhelming, multi-dimensional evidence of structural
  non-viability (every TF, every symbol, by-design cost refusal) with no path on its
  native timeframe — the clearest retire case.

## Recommended go-forward suite
**11 distinct strategies** (drop the `crypto_breakout` alias), of which **10 are
NEEDS_IMPROVEMENT** and **1 (scalping) is RETIRED**. **None is deployable with live
capital.** No new strategy is created: the evidence shows no previously-developed strategy
that is both profitable and superior to the existing suite, so the "new strategy" exception
is **not** triggered.

## Highest-confidence final state (the Phase-7 objective)
The suite is now in its highest-confidence honest state:
- **Technically correct:** all Type-A defects fixed across all 12; all adapters import,
  construct, and run error-free; operational system STABLE.
- **Fully characterized:** every strategy has a reconstructed hypothesis, verified
  entry/exit/regime logic, symbol- and timeframe-robustness evidence, and a classified
  issue list (A fixed / B documented / C quantified).
- **Honestly assessed:** 0 READY, 10 NEEDS_IMPROVEMENT, 2 RETIRED — backed by 324 matrix
  cells + 144 walk-forward cells.

## Next-step levers (non-tuning, optional, human-gated)
1. **Real open-interest feed** for oi_footprint, then re-test under the promotion rule.
2. **Resolve breakout's B1** confidence-vs-threshold inconsistency (human correctness ruling).
3. **Cross-symbol + walk-forward promotion gate** as the standing bar before any READY.
4. Remove the `crypto_breakout` alias registration (cleanup).

**Do not** pursue profitability via threshold/parameter optimization — the evidence shows
the gap is edge, not calibration, and tuning would manufacture in-sample artifacts (exactly
what the walk-forward test rejects). **Work stops here per the decision gate.**
