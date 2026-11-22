# E4-1 Freeze — XS-COMBO-V1 (2026-11-22)

Frozen BEFORE any 2025-01-01..2026-10-31 return was computed for this strategy.
Code: research/v2/strategies/xs_combo_v1.py + lib/panel.py + lib/backtest.py, combined sha256 prefix `b28908d1e6069656`.
Git commit containing this file is the freeze point.

## Development evidence (2020-01..2024-12)
Default settings net SR 1.92 (2x cost 1.75), 2022-24 SR 1.40; 36-setting grid median SR 1.69 (min 0.69),
2022-24 median 1.36 (min 0.61). Market/BTC beta ~0. ~200 trials logged in research/v2/results/trials.jsonl.

## Holdout pass criteria (declared now)
Holdout = 2025-01-01..2026-10-31 (~22 months; SE of annual SR ~0.74).
- **PASS**: net SR >= 0.75 at 1x cost AND net SR > 0 at 2x cost AND both 2025 and 2026 segments net positive
  AND no single symbol > 15% of absolute PnL.
- **STRONG PASS**: PASS and net SR >= 1.5.
- **FAIL**: anything else. On FAIL: no re-tuning on the holdout; return to dev research with a new idea.
