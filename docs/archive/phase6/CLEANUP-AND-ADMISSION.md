# Repository Cleanup + Strategy Admission Audit (Edge-Discovery → Product Completion)

**Date:** 2026-06-12. Transition from Edge-Discovery mode to Product-Completion mode.
Edge-discovery work is closed; this records the cleanup classification and the
strategy-admission decision. Reproducibility preserved (archived, not deleted).

## Part 1 — Cleanup classification

### ARCHIVED → `docs/archive/phase6/`
| item | from | rationale |
|---|---|---|
| edge-discovery harness | `research/edge_discovery/measurement/` | predictive-power research tooling; edge discovery closed |
| hypothesis runners + features | `research/edge_discovery/features/` | batch runners, price/spot cache, roadmap-A, eval_protocol — experimental |
| harness validation test | `tests/unit/test_edge_discovery_measurement.py` | tests archived research code |
| Phase-6/6.5/7 reports | `docs/reports/phase6/` | research history, rejected hypotheses, audit evidence (reproducibility) |
| derivatives (funding/OI) ingestion | `domain/ports/derivatives_data.py`, `infrastructure/data_sync/derivatives_*`, `application/use_cases/ingest_derivatives.py`, `interface/cli/derivatives_ingest.py`, `runner_derivatives_ingest.py`, its test | built for Phase-6 funding/OI research; NOT used by the 12 production strategies. **Un-wired from `bootstrap/container.py`** (removed 2 factories) so no unused research remains in the active execution path. |

### ACTIVE (kept in place)
- Production strategies (`infrastructure/strategies/`), engine, fusion, risk, execution.
- **Evaluation / profitability-audit framework:** `research/profitability_diagnostics/`
  (eval_matrix, eval_compare, eval_report, exit_forensics, eval_lifecycle_*,
  eval_mtf_portfolio, eval_microstructure) — required for Phase-C revalidation.
- Validated backtester (`infrastructure/backtest/`), data ingestion (OHLCV/MTF).
- **Phase-5 profitability audit reports** (`docs/reports/phase5/`) — audit evidence.

### REMOVE
- No git-tracked files met the REMOVE bar (temporary/duplicate/obsolete). Generated
  research outputs (`*_ledger.json`) were already git-ignored. Untracked research
  data caches (`data/research_cache/8h`, `8h_spot`, `data/history/raw/funding`) are
  not in any active execution path and are left on disk (regenerable; not committed).

## Part 2 — Strategy Admission Audit

**Default decision: DO NOT ADD.** A research signal may enter production only if ALL
of: positive net expectancy · survives realistic costs · OOS-validated · statistically
significant (post-correction) · broad across symbols · economically explainable ·
demonstrably superior to existing strategies.

| research signal | best evidence | conditions met | decision |
|---|---|---|---|
| revert_highvol_3 (high-vol reversion) | net −8.7 bps @10bps; OOS IC +0.043 | cost ❌ | **REJECTED** |
| regime_revert_highvol_downtrend | net +38 bps@10bps, t=2.5, OOS +0.078 | cost ✅ but significance ❌ (not family-corrected), breadth ❌ (9/24), superiority ❌ | **ARCHIVED** (near-miss; needs wider-universe/holdout confirmation) |
| funding_revert (carry) | falsified on wider universe (mean IC −0.003) | none | **REJECTED** |
| cross-sectional / momentum / reversion / basis / factors / ML-combo / seasonality | IC≈0, cost-negative | none | **REJECTED** |

**ADDED: 0 · ARCHIVED: 1 (regime_revert_highvol_downtrend) · REJECTED: rest.**
No research strategy satisfied all admission conditions; none integrated or exposed
in production configuration. The single near-miss is archived with its evidence for a
possible future, separately-approved confirmation program. The active production
strategy universe is unchanged (the original 12).
