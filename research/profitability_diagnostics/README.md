# Phase 5 — Profitability Diagnostic Tooling

Reproducible analysis scripts behind the Phase-5 diagnostics. Moved here from the
(gitignored) `tasks/` tree so the *method of record* is version-controlled
(CLAUDE.md validation standard #18: performance reports must be reproducible).

**Run from the repo root** (paths are repo-root-relative), e.g.:

    .venv/bin/python3 research/profitability_diagnostics/eval_matrix.py

Inputs/outputs live under `data/results_storage/` (matrices, dumps) and the
narrative reports under `tasks/phase5-*/` (still gitignored — regenerable).

| script | purpose | reads | writes |
|---|---|---|---|
| `eval_matrix.py` | 108-cell edge-measurement matrix (resumable) | history CSVs (app) | `data/results_storage/eval_matrix.json` |
| `eval_compare.py` | PRE vs POST exit-fix comparison | `eval_matrix(_PRE).json` | `tasks/phase5-evaluate/exit-fix-pre-post-comparison.md` |
| `eval_report.py` | per-strategy assessment + ranking | `eval_matrix.json` | report md |
| `exit_forensics.py` | exit-path forensics instrumentation run | history (app) | forensics output |
| `eval_lifecycle_dump.py` | per-trade lifecycle capture (90d) | history (app) | `data/results_storage/lifecycle_trades.json` |
| `eval_lifecycle_forensics.py` | MFE/MAE/exit/R distributions + economic viability | `lifecycle_trades.json` | `tasks/phase5-profitability/ep5.3-*.md` |
| `eval_mtf_portfolio.py` | E-P5.4 MTF-conflict + correlation/portfolio risk | `lifecycle_trades.json` + 1m CSVs | `tasks/phase5-profitability/ep5.4-*.md` |
| `eval_microstructure.py` | E-P5.5 execution-cost decomposition + sensitivity | `lifecycle_trades.json` | `tasks/phase5-profitability/ep5.5-*.md` |

Notes:
- App-coupled scripts (`eval_matrix`, `exit_forensics`, `eval_lifecycle_dump`)
  resolve the repo root via 3×`dirname(__file__)` — they must stay 2 levels deep
  (`research/profitability_diagnostics/`).
- 1m history CSV timestamps are **epoch seconds** (`pd.to_datetime(..., unit="s")`).
- These reproduce a frozen result; they do not re-tune or modify strategies.
