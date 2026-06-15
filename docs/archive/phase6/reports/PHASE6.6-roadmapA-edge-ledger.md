# Phase 6.6 — Roadmap A Cumulative Edge Ledger

_Free-data hypothesis classes run through the full Phase-6 protocol (HAC IC · purged/embargoed CV · multiple-testing · OOS split · cost gate). Default REJECT. PROMOTE only if significant + cross-symbol + OOS-stable + robustly net-positive after 10 bps. No optimization/sweeps._

| # | class | taxonomy | IC@h | breadth sig | OOS IC | gross bps | net@10 | t(net) | n | verdict |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | basis_zscore_revert | C3_basis | +0.014@1 | 0/24 | +0.038 | +1.0 | -9.0 | -9.7 | 75413 | **REJECT** |
| 2 | coint_spread_revert | C2_coint | +0.074@9 | 5/12 | +0.032 | +21.5 | +11.5 | +1.4 | 4260 | **REJECT** |
| 3 | factor_low_beta | C2_factor | +0.003@9 | 2/24 | -0.003 | +8.7 | -1.3 | -0.2 | 8409 | **REJECT** |
| 4 | ml_logit_combination | C8_ml | +0.012@1 | 2/24 | +0.012 | +6.8 | -3.2 | -2.0 | 23091 | **REJECT** |
| 5 | regime_revert_highvol_downtrend | C5_regime | +0.081@9 | 9/24 | +0.078 | +48.0 | +38.0 | +2.5 | 3125 | **REJECT** |
| 6 | seasonality_slot_of_day | C6_seasonal | -0.025@1 | 7/24 | -0.011 | -2.4 | -12.4 | -13.7 | 77932 | **REJECT** |

**Classes evaluated:** 6 · **PROMOTED:** 0 (none)

- ❌ **basis_zscore_revert** rejected: harness=ARCHIVE; breadth 0/24; cost net -9.0bps t=-9.7 n=75413
- ❌ **coint_spread_revert** rejected: harness=ARCHIVE; cost net +11.5bps t=+1.4 n=4260
- ❌ **factor_low_beta** rejected: breadth 2/24; OOS IC -0.003 vs IS +0.003; cost net -1.3bps t=-0.2 n=8409
- ❌ **ml_logit_combination** rejected: breadth 2/24; net -3.2bps t=-2.0
- ❌ **regime_revert_highvol_downtrend** rejected: harness=ARCHIVE
- ❌ **seasonality_slot_of_day** rejected: breadth 7/24; cost net -12.4bps t=-13.7 n=77932

## Analyst note — Roadmap A exhausted (0 promoted), but one coherent near-miss

**`regime_revert_highvol_downtrend` (class 5) is the strongest signal found in all of
Phase 6** and the only one to *clear costs*: 3-day-hold reversion entered in a
**high-volatility + downtrend** regime — IC@3d **+0.081**, **OOS +0.078 (holds)**,
gross +48 bps, **net @10 bps = +38.0 bps/trade, t=+2.5**, n=3,125.

**Correctly REJECTED** (not promoted) for disciplined reasons:
1. **Multiple-testing:** t=+2.5 (p≈0.012 uncorrected) does NOT survive the cumulative
   family across all classes/horizons — the harness gate archived it.
2. **Breadth:** 9/24 symbols same-sign-significant (37.5%) — not a clear cross-symbol
   majority; edge concentrated in a subset.

**Why it still matters:** it is the *first* signal to beat the ~10 bps cost cliff —
because it is **low-turnover (3-day hold)** and **regime+direction conditioned**
(panic reversion), and it is OOS-stable. Not a tradeable edge, but the **single
highest-priority candidate** for a dedicated, pre-registered follow-up: wider universe
(test the 37.5% breadth), longer history (more independent 3-day windows → real
multiple-testing power), true forward holdout. Secondary near-miss:
`coint_spread_revert` (net +11.5 bps but t=+1.4, insignificant).

**Verdict:** Roadmap A (free-data) is exhausted with **no confirmed tradeable edge**,
but it narrowed the search to one coherent, cost-surviving, low-turnover direction —
found on **free data**, reinforcing the 6.5 conclusion that paid acquisition is
premature.
