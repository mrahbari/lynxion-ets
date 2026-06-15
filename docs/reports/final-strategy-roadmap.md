# Final Strategy Roadmap

**Date:** 2026-06-12. Ranked plan for remaining work on the 12 fixed production
strategies, after Strategy Rehabilitation. Companion to `strategy-rehabilitation.md`,
`strategy-readiness-matrix.md`, `production-readiness-report.md`,
`candidate-calibration-fixes.md`, `hypothesis-fidelity-review.md`.

**Status:** READY 0 · NEEDS_IMPROVEMENT 11 · NON_VIABLE 1. All Type-A defects resolved;
suite is correct + measurable but not profitable. **Not deployable.**

## What is DONE (this program)
- **Direction-B rewire:** every strategy evaluated through its real `generate_signal`.
- **HFR fixes:** vwap_reversal (0→67; slope unit-bug + `%24` session + σ-band), scalping
  (volume-units; reaches its hypothesis gate).
- **Rehab Type-A fix:** liquidity directional bug (0→61 BUY).
- **Dominant-constraint discovery:** 1m cost-incompatibility (TP ≈ 0.10% ≪ 0.30% cost;
  breakeven ≈ 15m), empirically confirmed by 1h/15m re-runs.
- **Five deliverables produced; Type-B register prevents curve-fitting.**

## Ranked roadmap (highest-leverage first)

### 1. Re-baseline the entire suite on a cost-viable timeframe (≥15m; recommend 1h) — **CRITICAL**
The single highest-value action. 1m is structurally unviable; `eval_matrix_1h.json` is the
first viable baseline. Make ≥15m the canonical evaluation/deployment timeframe (a
data/config correction, not a strategy change). *Decision flag:* confirm the production
target timeframe — if it must be 1m, the suite is NON_VIABLE-on-1m and work stops.
*Impact: very high (changes every verdict's substrate). Risk: low.*

### 2. Impose cross-symbol + cross-window stability gates before any READY claim — **HIGH**
Current best cells are single-symbol positives (BTC/ETH) that collapse on SOL. Require a
candidate to be positive (or non-catastrophic) across BTC/ETH/SOL and 90/180/365d.
*Impact: high (prevents false READY). Risk: low.*

### 3. Resolve oi_footprint's data dependency — **HIGH (data-gated)**
It posts the best single positive cell (ETH 365d +165 GO) but uses volume×1.5 as an OI
proxy. Wire a real open-interest feed (data is present under `data/history/raw/open_interest/`)
before trusting its edge. *Impact: high for one strategy. Risk: medium (data plumbing).*

### 4. Walk-forward / out-of-sample validation on the chosen timeframe — **HIGH**
All current evidence is in-sample backtest. No live decision without WFO. *Risk: low.*

### 5. Review the two borderline Type-B → possible Type-A reclassifications — **MEDIUM**
`candidate-calibration-fixes.md` B-1 (breakout confidence-scale vs `min_confidence` gate,
blocks all trades) and B-3 (vwap_reversal dead rejection path). Human review whether each
is a mis-scaled *formula* (defect → fix) or a deliberate *threshold* (leave). *Risk: medium
(hypothesis drift).*

### 6. Complete the canonical 1m matrix only if a 1m mandate is confirmed — **LOW**
The 1m matrix is partial (17 BTC cells) and ~32h to finish (O(n²) backtester at 365d×1m).
It already establishes the 1m structural finding; completing it adds little unless 1m is
the confirmed production timeframe. *Impact: low. Risk: low.*

## Explicitly NOT on the roadmap (out of bounds)
- New strategies / new hypothesis classes / edge-discovery / Phase-6 research.
- Loosening entries to force trades; Hyperopt; parameter sweeps; curve-fitting;
  optimization against historical results.
- Redesigning any strategy hypothesis.

## Honest synthesis
Rehabilitation succeeded at its engineering objective — the suite is correct, measurable,
and free of Type-A defects — and it produced the decisive insight (timeframe/cost) that
prior phases missed. But **deployable trading systems require demonstrated edge, and none
exists**: on 1m the geometry can't clear costs; on a viable timeframe the strategies lack
stable cross-symbol expectancy. The path forward is timeframe correction + stability-gated
re-evaluation + WFO + the oi_footprint data fix — not parameter tuning. Until a strategy
shows positive, stable, out-of-sample expectancy, the correct verdict remains
NEEDS_IMPROVEMENT (or NON_VIABLE), and the system is not production-ready.
