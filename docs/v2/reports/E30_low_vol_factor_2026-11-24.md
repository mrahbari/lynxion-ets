# E30 — cross-sectional low-volatility factor (2026-11-24)

Pre-registered and committed before the run (research/v2/experiments/e30_low_vol_factor.py). XS-COMBO-V1
panel, mask, costs and construction. Net Sharpe:

| signal | DEV 2020-24 | HOLDOUT 2025-26 | by year |
|---|---|---|---|
| XS-COMBO-V1 (reference, reproduces E4) | 1.82 | 1.39 | 2025 2.25, 2026 0.55 |
| LOWVOL alone | -0.21 | -0.71 | negative 2021, 2023, 2025, 2026 |
| COMBO4 (V1 + low vol) | 1.43 | -0.10 | 2025 0.51, 2026 -0.77 |

**FAIL / not better.** The published low-volatility premium does not hold on liquid USDT-M perps net of costs and
funding (high-vol coins carry the funding the sleeve harvests); adding it damages XS-COMBO. Nothing changed.
