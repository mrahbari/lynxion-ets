# E29 — daily Donchian-ensemble trend with volatility targeting (2026-11-24)

Source: Zarattini, Pagani, Barbon, "Catching Crypto Trends" (SFI RP 25-80, 2025). Pre-registered and committed
before the run (research/v2/experiments/e29_daily_trend_ensemble.py). 10 liquid USDT-M perps, Binance 1h ->
daily, lookbacks 10-250 days, 25 % vol target (cap 200 %), one-day lag, 10 bp per turnover, real funding.

| variant | window | net Sharpe | CAGR | vol | max DD | BTC Sharpe / max DD | beta | alpha | turnover/yr |
|---|---|---|---|---|---|---|---|---|---|
| long-only | DEV 2020-24 | 1.24 | 11.0 % | 8.7 % | -11.2 % | 1.12 / -76.7 % | 0.08 | 5.3 % | 2.7 |
| long-only | HOLDOUT 2025-26 | **-0.38** | -3.3 % | 8.0 % | -11.7 % | -0.02 / -53.0 % | 0.10 | -2.9 % | 4.1 |
| long-short | DEV | 0.72 | 6.9 % | 10.1 % | -19.2 % | | 0.00 | 6.9 % | 5.3 |
| long-short | HOLDOUT | -0.16 | -3.0 % | 13.5 % | -13.2 % | | -0.16 | -2.3 % | 8.6 |

Long-only Sharpe by year: 2020 1.99, 2021 1.47, 2022 -1.43, 2023 1.74, 2024 1.48, 2025 -0.47, 2026 -0.26.
**FAIL** (HOLDOUT Sharpe below 0.4). The literature result reproduces in trending years and fails in the
2025-26 range/decline regime; drawdown control vs BTC holds in both windows (-12 % vs -53 % / -77 %).
Not built. Kept as the reference daily-trend design if a pre-defined regime filter is ever validated.
