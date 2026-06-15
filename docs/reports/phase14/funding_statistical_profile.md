# Phase 14 — Funding Statistical Profile

**Date:** 2026-06-13. Analysis only — descriptive statistics of the funding series themselves (Task 2).
No forward returns, no signals, no strategy, no profitability. All 24 symbols, ~3 years.

## Funding distribution (per 8h interval, % of notional)

| sym | n | mean% | std% | p1% | p99% | %positive |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 3285 | +0.0068 | 0.0090 | −0.008 | +0.047 | 84.7 |
| ETH | 3285 | +0.0070 | 0.0095 | −0.010 | +0.049 | 85.1 |
| SOL | 3285 | +0.0047 | 0.0162 | −0.028 | +0.061 | 69.3 |
| UNI | 3285 | +0.0081 | 0.0103 | −0.013 | +0.052 | 85.8 |
| LTC | 3285 | +0.0080 | 0.0110 | −0.010 | +0.057 | 84.4 |
| LINK| 3285 | +0.0079 | 0.0113 | −0.016 | +0.057 | 84.2 |
| DOGE| 3285 | +0.0075 | 0.0117 | −0.013 | +0.058 | 79.9 |
| BNB | 3285 | −0.0020 | 0.0193 | −0.083 | +0.039 | 25.1 |
| BCH | 3285 | −0.0033 | 0.0187 | −0.062 | +0.045 | 49.2 |
| TRX | 3285 | −0.0000 | 0.0187 | −0.070 | +0.043 | 62.2 |
| FLOW| 4155 | −0.0023 | 0.0579 | −0.171 | +0.069 | 76.0 |
| ZEC | 3285 | −0.0000 | 0.0646 | −0.169 | +0.058 | 79.6 |
| *(others 0.002–0.008 mean, 0.012–0.020 std, 66–82% positive)* | | | | | | |

**Findings**
- **Strong positive bias (perp contango).** 19/24 symbols are positive >65% of the time; BTC/ETH/UNI/LTC
  ≈85%. Longs pay shorts most of the time → the baseline (unconditional) funding regime is "mildly
  positive". This is structural, not predictive.
- **Persistent negative-funding names:** BNB (only 25% positive, mean −0.002%) and BCH (49%, −0.003%)
  sit in backwardation far more often — distinct positioning regimes.
- **Volatility tiers:** majors are tight (BTC σ=0.009%, ETH 0.0095%); mid-caps 0.012–0.020%; **FLOW/ZEC
  σ≈0.06%** dominated by the tail events flagged in the audit (winsorise before pooling).

## Funding persistence (autocorrelation)

| metric | range across symbols | majors (BTC/ETH) |
|---|---|---|
| lag-1 autocorr (next 8h) | 0.49 – 0.83 | **0.83 / 0.81** |
| lag-3 autocorr (24h) | 0.35 – 0.76 | **0.76 / 0.72** |

- **Funding is highly persistent.** Today's funding strongly predicts the next interval's funding
  (ρ₁ ≈ 0.6–0.83). This is the most robust statistical property in the dataset: funding *regimes* last,
  they don't whip back interval-to-interval.
- **Caveat:** persistence of funding ≠ predictiveness of *price*. High autocorrelation only says funding
  is a slow-moving state variable. Whether that state forecasts returns is the predictive question
  (`funding_predictive_analysis.md`) — and the answer there is mostly "no".
- FLOW/ZEC show the lowest persistence (0.49/0.60) — consistent with their tail-event-driven series.

## Regime frequency

Regimes defined per symbol on its own funding distribution:
- **extreme_neg** = funding ≤ p10 → clean **10.0%** of the time for every symbol (p10 is well-separated).
- **extreme_pos** = funding ≥ p90 → ranges **10%–65%** across symbols. This wide range is a *tie
  artifact*: symbols that sit at the venue default rate (≈+0.01%) for long stretches have many values
  equal to p90, so `≥ p90` captures a large block (e.g. SAND 56%, ZEC 65%). Symbols with a smooth upper
  tail give the clean ~10% (DOGE, BNB, ETC, XRP). **Implication:** the "extreme positive" bucket is a
  *soft* "elevated funding" bucket for many symbols, not a sharp tail. The **extreme_neg bucket is clean
  and comparable across all symbols** — which matters, because that is where the only predictive thread
  appears.

## Symbol-by-symbol summary

- **Majors (BTC/ETH):** tightest distributions, strongest persistence, most positive-biased — the
  cleanest series and the focus of the predictive analysis.
- **SOL:** wider (σ=0.016%), more two-sided (69% positive) — behaves more like a mid-cap.
- **BNB / BCH / TRX:** backwardation-prone (low %positive) — structurally different funding regime.
- **FLOW / ZEC:** outlier-dominated; profile them only after winsorising.
- **TON:** 4h cadence — its statistics are on a different settlement clock and are **not** comparable
  to the 8h cohort.

## Takeaway (statistical, pre-predictive)

The funding series are **clean, persistent, and structurally positive-biased**, with a well-defined
extreme-negative tail and a fuzzy extreme-positive tail. Persistence is the dominant feature. None of
these descriptive properties, on their own, establish predictive information about price — that is
tested next.
