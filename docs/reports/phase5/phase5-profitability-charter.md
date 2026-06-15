# Phase 5 — Profitability Discovery Pipeline (continuous execution)

**Mission:** determine whether this system can be consistently profitable in
real conditions, and identify+remove every profitability blocker. Not task
completion — profitability verdict.

**Mode:** continuous autonomous pipeline across E-P5.2 → E-P5.3 → E-P5.4 →
E-P5.5. Diagnosis before optimization. Root-cause before symptom. NO parameter
tuning / Hyperopt / curve-fitting until the evaluation framework is proven
trustworthy.

## Execution order (dependency × profitability impact)

1. **E-P5.2 Edge Measurement** — the trustworthy measurement baseline. *Status:
   evaluation framework largely corrected (two exit-layer bugs fixed; see
   blocker ledger). Full 108-matrix POST re-run + fresh assessment in progress.*
2. **E-P5.3 Trade Lifecycle & Entry Precision** — HIGHEST near-term profit
   impact: raises expectancy on EXISTING signals (entry packages w/ SL/TP ladder
   + R:R gate; breakeven/trailing/partial/time-stop lifecycle; scale-in). No new
   edge required. Diagnose first via MFE/MAE forensics already instrumented.
3. **E-P5.4 MTF & Portfolio Intelligence** — cuts losing trades (counter-HTF
   entries; correlated-stacking). Real MTF score + live correlation/heat +
   structure-aware SL/TP.
4. **E-P5.5 Microstructure & Adaptation** — Tier 3, needs new data (L2/trades/
   funding/OI), additive edge. LAST; only after 5.2/5.4 prove OHLCV strategies
   are measurable+improvable.

## Per-strategy classification (assign in every assessment)

`Validated Edge` · `Near Profitability` · `Research Ready` · `Needs Redesign` ·
`Insufficient Evidence`. NEVER "remove" unless the trading hypothesis itself is
disproven. For losers, identify: implementation / regime-mismatch / execution /
trade-management / risk-management / data-quality deficiency.

## Mandatory evaluation areas → epic mapping

- **A Edge Measurement** (expectancy/PF/sharpe/sortino/drawdown/recovery-factor/
  regime) → E-P5.2 (extend ledger with recovery factor).
- **B Trade Lifecycle** (entry precision/stop/TP quality/partials/trailing/
  breakeven/scale) → E-P5.3.
- **C MTF** (alignment/conflict/score/regime sync) → E-P5.4 T1.
- **D Portfolio** (correlation/concentration/heat/capital efficiency/cross-
  strategy) → E-P5.4 T2.
- **E Microstructure** (spread/liquidity/slippage/session/stop-hunts/fake-
  breakouts/absorption/sweeps) → E-P5.5 T1/T2 (+ some testable on OHLCV now).
- **F Adaptation** (regime/volatility/risk/sizing adaptation) → E-P5.4 T3 +
  E-P5.5 T3.

## Blocker handling (every blocker) — Measure → Diagnose → FIX → Re-evaluate

Phase 5 is NOT audit-only. Diagnosis is the first half; remediation is the
mandate. For EVERY validated blocker in E-P5.3 / E-P5.4 / E-P5.5:

1. **Quantify impact** (expectancy / P&L / win-rate, in R and $).
2. **Estimate profitability upside** if fixed.
3. **Create a remediation epic/task** under this dir (`remediation-<id>.md`).
4. **Prioritize** the remediation backlog by expected ROI
   (upside × confidence ÷ implementation effort).
5. **Implement** the remediation — UNLESS it hits a true approval gate
   (production assets / real money / data loss / security / legal-compliance /
   materially-different architecture / irreversible / external paid service).
   Respect frozen-baseline discipline: do not mutate the backtester until the
   measurement baseline is frozen; remediation edits land on top of the freeze
   and are re-measured against it.
6. **Re-run the affected evaluations** (targeted re-eval, then matrix where the
   change is broad).
7. **Measure profitability improvement** vs the frozen baseline; record the
   delta in `blocker-ledger.md` and flip the blocker status to FIXED/PARTIAL
   with the measured numbers.

Loop diagnosis→remediation→re-eval until blockers are exhausted or an approval
gate appears. Goal = systematically REMOVE the highest-ROI blockers and measure
the resulting improvement, not merely list them.

## Per-epic output template (MANDATORY, end of every epic)

1. Findings  2. Root causes  3. Profitability impact (quantified)  4. Recommended
fixes  5. Estimated upside if fixed  6. Priority ranking.
For every deficiency: quantify impact → rank impact → identify root cause →
estimate profitability upside if fixed.
**Then remediate (not optional):** 7. Remediation epics created (ROI-ranked)
8. Remediations implemented this epic  9. MEASURED improvement vs frozen
baseline (re-eval deltas) + updated blocker statuses.

### Epic-specific questions to answer explicitly

- **E-P5.3 (lifecycle):** expectancy lost due to — stop placement / take-profit
  placement / missing breakeven / missing trailing / missing partial exits.
  Required distributions: MFE, MAE, exit-type, R-multiple, time-in-trade, TP-hit,
  SL-hit; + breakeven / trailing / partial-TP OPPORTUNITY analyses. Objective =
  quantify expectancy left on the table, NOT redesign yet.
- **E-P5.4 (MTF/portfolio):** profitability lost to MTF conflicts; profitability
  lost to missing portfolio intelligence; risk hidden by correlation exposure.
- **E-P5.5 (microstructure):** profitability lost to spread / slippage / liquidity
  constraints; which strategies are most microstructure-sensitive.

## Cumulative blocker ranking

Maintain a single cumulative profitability-blocker ranking across all epics in
`blocker-ledger.md` (rank by quantified profitability impact). Phase-5 final
deliverable = a prioritized roadmap of exactly what separates the current system
from sustainable profitability.

## Phase-5 SYNTHESIS report (after E-P5.5; do not stop after producing it)

Consolidate E-P5.2/5.3/5.4/5.5 into `phase5-profitability-synthesis.md`:
1. **Profitability Blocker Ranking** — ordered 3 ways: by estimated impact, by
   implementation effort, by expected ROI.
2. **Strategy Status Matrix** — every strategy classified: Validated Edge /
   Near Profitability / Research Ready / Needs Redesign / Insufficient Evidence.
3. **Profitability Gap Analysis** — gap between current / break-even / target.
4. **Improvement Roadmap** — ordered by expected profit impact × confidence ×
   implementation complexity.
5. **Candidate Strategies** — closest-to-profit / highest-upside / highest-
   confidence / most-regime-dependent / most-execution-sensitive / most-
   microstructure-sensitive.
6. **Readiness Assessment** — for E-P5.6 Strategy Refinement, WFO Validation,
   Fusion Fidelity Validation, Paper Trading.

Then continue: if blockers remain → create follow-up epics/tasks under this
hierarchy, prioritize by expected profit impact, keep executing. Stop only when
no major blocker remains, an approval gate appears, or a defensible profitability
verdict is reached.

## Artifacts

- `blocker-ledger.md` — every profitability blocker, impact, status.
- Per-epic diagnosis reports under this dir (`docs/reports/phase5/`).
- Evaluation harness lives in `research/profitability_diagnostics/` (eval_matrix.py, eval_report.py,
  eval_compare.py, exit_forensics.py, eval_lifecycle_*.py, eval_mtf_portfolio.py,
  eval_microstructure.py); data of record in `data/results_storage/`.
