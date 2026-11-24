# E32 — cross-sectional skewness factor (2026-11-24)

Source: skewness premium (Fernandez-Perez et al. 2018; Baltas 2019), replicated for traditional futures in
github.com/rolling-panda-san/notebooks (operator link). Pre-registered and committed before the run
(research/v2/experiments/e32_skewness_factor.py); XS-COMBO-V1 panel, costs and construction.

| signal | DEV net / gross Sharpe | HOLDOUT net / gross Sharpe | by year |
|---|---|---|---|
| XS-COMBO-V1 (reference) | 1.82 / 1.52 | 1.39 / -0.02 | 2025 2.25, 2026 0.55 |
| SKEW (long negative skew, short positive skew, 60 d) | -0.31 / -0.06 | -0.38 / +0.19 | alternates sign every year |
| COMBO4S (V1 + skew) | 1.45 / 1.24 | 0.91 / -0.20 | 2026 -0.34 |

**FAIL / not better.** No skewness premium on liquid USDT-M perps; adding it dilutes XS-COMBO. Nothing changed.
Repo review (other notebooks): time-series momentum = E29 / Codex C-14 (failed holdout; the repo author also
notes weakening since 2015); carry = XS-COMBO (validated); Connors short-term = E25 MR1 (failed); basis
momentum/reversal has no clean single-contract perp analogue (perp basis convergence: Codex C-20/24/25
rejected); intraday/overnight equity effects do not map to a 24 h market.
