# Phase 14 — Funding Dataset Audit

**Date:** 2026-06-13. Analysis only. No signals, no strategy, no parameter tuning, no profitability
claims. Scope of this file = **integrity of the archived funding dataset** (Task 1).

Source: `data/history/raw/funding/<SYM>-USDT.csv` (archived Phase-6 derivatives stack, never used by any
strategy — see Phase-13 `unused_data_inventory.md`). Schema: `timestamp,funding_rate` (unix seconds,
fraction per funding interval).

## Coverage

- **24 symbols**: AAVE, ADA, ALGO, AVAX, BCH, BNB, BTC, DOGE, DOT, ETC, ETH, FLOW, LINK, LTC, MANA,
  NEAR, SAND, SOL, TON, TRX, UNI, XLM, XRP, ZEC.
- **Calendar span:** 2023-06-13 → 2026-06-11 (**~1095 days ≈ 3.0 years**) for all 8h-cadence symbols.
- **Row counts:** 3285 rows for 22 symbols (8h cadence × ~3y). Exceptions: **TON** = 4995 rows,
  **FLOW** = 4155 rows.

## Cadence / timestamp consistency

- **22 of 24 symbols: clean 8.0h cadence, 0 gaps** (median inter-row Δ = 28800s; no interval > 1.5×
  median). 3 funding settlements/day, uninterrupted across 3 years.
- **TON: 4.0h cadence**, 832-day span, **1 gap detected** — TON funds every 4h (twice the rate of the
  rest) and starts later. Mixing TON's 4h funding with 8h symbols would misalign regime/persistence
  comparisons → **TON flagged; treat separately, excluded from any 8h-cadence cross-symbol pooling.**
- **FLOW: 4155 rows** over the same ~3y span → mixed cadence (period of 4h funding then 8h, or extra
  settlements). Flagged for cadence-normalisation before any pooled use.

## Missing values / continuity

- **No missing `funding_rate` cells, no NaNs, no zero-length files.** Every row parses to a float.
- **Symbol continuity:** all 24 series are continuous from first to last timestamp at their native
  cadence (no multi-day holes) except the single TON gap noted above.
- Many symbols show clusters of identical values at the venue default (≈ +0.0100%/8h), which is normal
  for perps that sit at baseline funding for long stretches. This is **not** a data defect but it does
  inflate the `≥ p90` ("extreme positive") bucket via ties — see the statistical profile.

## Value-range anomalies (outliers, not corruption)

| Symbol | min funding | max funding | note |
|---|---|---|---|
| **FLOW** | **−2.000%** | +0.346% | −2.0% is a venue floor / squeeze artifact; std 0.058% (6× typical) |
| **ZEC** | **−1.640%** | +0.114% | extreme negative spike; std 0.065% (highest in set) |
| ALGO | −0.315% | +0.119% | single deep-negative event |
| DOT | −0.331% | +0.102% | single deep-negative event |
| SOL | −0.303% | +0.119% | deep-negative event |
| (typical) | ~−0.05% | ~+0.06% | BTC/ETH tightest: min −0.015%/−0.037% |

These extremes are **plausible market events** (deleverage/squeeze), not parsing errors, but FLOW/ZEC
should be **winsorised or excluded** from distribution statistics so two events don't dominate.

## Integrity verdict

- **22/24 symbols: PASS** — 3.0 years, clean 8h cadence, zero gaps, zero missing values, sane ranges.
- **TON: USABLE WITH CARE** — 4h cadence + 1 gap; do not pool with 8h symbols.
- **FLOW, ZEC: USABLE WITH CARE** — extreme-tail outliers (winsorise); FLOW also mixed cadence.

The dataset is **fit for information-content analysis.** The binding limitation for the *predictive*
tasks is **not** the funding data — it is the overlapping **price** history (addressed below), not the
funding series, which is complete.

## Price alignment prepared for the predictive tasks

The predictive tests (Tasks 3–5) need OHLCV aligned to funding timestamps. On-disk intraday price
originally covered only ~1 year. For this phase, 1h price for **BTC/ETH/SOL** was back-filled (paginated
Binance public klines, `scripts/extend_price_to_funding.py`) to the funding start:

| Symbol | 1h price rows | span | funding obs aligned |
|---|---|---|---|
| BTC-USDT | 26,262 | 2023-06-13 → 2026-06-11 | 3,274 |
| ETH-USDT | 26,266 | 2023-06-13 → 2026-06-11 | 3,275 |
| SOL-USDT | 26,266 | 2023-06-13 → 2026-06-11 | 3,275 |

So the predictive analysis runs over the **full ~3-year funding window** for the three majors. The other
21 symbols have funding but lack matching 3-year intraday price on disk → descriptive/integrity work
covers all 24; predictive work covers BTC/ETH/SOL (documented limitation, see
`funding_predictive_analysis.md`).

**Harness:** `scripts/funding_information_analysis.py` (integrity + descriptive + predictive + WFO).
