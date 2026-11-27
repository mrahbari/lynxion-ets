# Implementation-level study of four open-source crypto stat-arb repositories (2026-11-27)

**Scope.** Source code read; nothing was run or copied into Lynxion.
- Repos were cloned read-only (`git clone --depth 1`) into the session scratchpad.
- Notebook code cells were extracted to text.
- No production code, strategy or configuration was changed.
- Repository-reported results are treated as unverified.

## 1. aurelien-gentile/crypto-pairs-trading (commit 51e3390)

Files: `2_arbitrage_backtest.ipynb` (cells extracted), `3_arbitrage_production_tool.ipynb`.

**How it works.**
- **Data:** daily Bybit perp closes.
- **Pre-filter:** absolute Pearson correlation over a 365-day formation window, top 500 pairs. Optionally on "homoskedastic" log prices: returns divided by an EWMA volatility with k = 0.9, then cumulated (`compute_homoskedastic_returns`).
- **Pair selection:** Johansen trace test at 99 % on the formation window. Each coin is used once and 20 pairs are kept (`cointegration_tests`).
- **Trading** (`run_backtesting`):
  - OLS hedge on price levels.
  - Each day of the 180-day trading period: if the spread is beyond the formation mean ± 2σ, take the mean-reverting position; inside the band, flat.
  - It is therefore in a position only while the spread is outside the band, with no "hold until mean" exit.
  - Six overlapping 180-day "desks" start every 30 days; the portfolio is their average.
  - Portfolio stop at −10 % per pair.

**Defects in the code (implementation quality: low).**

| Defect | Where |
|---|---|
| Engle-Granger branch accepts a pair when `p_value > 0.5`, i.e. when it is *not* cointegrated. Johansen is the default, so the headline is unaffected, but the alternative path is wrong | `cointegration_tests` |
| `if s1 in used_cryptos or s1 in used_cryptos`: s2 is never checked, so a coin can appear in two pairs | `cointegration_tests` |
| Trading fees are computed (`comission_flag`) but never subtracted. The only cost is a flat 4 bp/day "funding" on both legs | `run_backtesting` |
| Legs are sized 0.5 / 0.5 notional, not by the hedge ratio, so the book is not spread-neutral | `run_backtesting` |
| 500 random parameter sets are scored on the last 30 % and filtered by p < 0.01, then a random forest is fitted on the p-values. This is selection on the evaluation window | parameter search |

**Reusable idea: overlapping desks / staggered tranches.**
- Averaging staggered portfolios removes the dependence on one start date.
- For Lynxion this maps directly to the rebalance-phase problem (E38: the holdout Sharpe ranges 0.50–1.77 by weekday).

## 2. adnanegrb/statistical-arbitrage-crypto (commit d23e74d)

Files: `analysis/cointegration.py`, `analysis/pair_screening.py`, `analysis/spread.py`, `backtest/engine.py`,
`backtest/signals.py`, `backtest/sizing.py`, `tests/test_bias.py`.

**How it works.**
- **Data:** 4h Binance closes for 33 tokens with category labels.
- **Screening:** correlation ≥ 0.7, then both Johansen trace (95 %) and ADF on the OLS residual must pass (`is_cointegrated`).
- **Walk-forward:** 252-bar train, 63-bar test (`run_walk_forward`).
  - Hedge ratio, spread mean/std and half-life are fitted on train only and frozen.
  - Enter at |z| ≥ 2, exit at |z| < 0.5, stop at |z| > 3.5 (`generate_positions`).
  - Positions are lagged one bar; 5 bp per position change.
- **Sizing:** quarter-Kelly from the pair's own out-of-sample trades (`kelly_fraction_from_returns`).

**Defects.**
- Pair *screening* runs once on the full history (`main.py` → `screen_pairs(price_matrix)`) before the walk-forward. The choice of pairs uses future data, so results are biased upward.
- Kelly is sized from the same out-of-sample trades it is then applied to.
- Funding is ignored.

**Reported result (honest, and it agrees with our E33).**
- Same-category pairs: mean OOS Sharpe −0.32 (15 pairs). Cross-category: −0.29 (136 pairs). 93 of 151 negative.
- The author attributes the high pass rate (31 %) to shared market beta. This is the negative result despite the
  selection bias in its favour.

**Reusable ideas.**
- The **funnel report**: universe → correlation survivors → cointegrated → same-category, saved to CSV.
- The **economic-link split** (same vs cross category) as a control for spurious statistical relationships.
- **Half-life** reported as a diagnostic, not used to tune.

## 3. abailey81/Crypto-Statistical-Arbitrage (commit 44b718e)

About 227k lines across 219 files: data collectors for many CEX/DEX venues, pairs, futures curve, funding arb, options,
reporting. The README reports Sharpe 1.61 and **5.81**.

**Read in detail.** `strategies/funding_rate_arb/cross_venue.py`, `strategies/futures_curve/funding_rate_analysis.py`,
`backtesting/transaction_costs.py`.

- **`CrossVenueFundingArbitrage`.**
  - Venue fee table (Binance taker 4 bp, Bybit 6 bp, Hyperliquid 2.5 bp and 1h funding, dYdX, GMX).
  - Funding normalised per venue interval.
  - **Entry** when the annualised spread is ≥ 5 % and 30-day expected carry is more than 2× round-trip costs.
  - **Exit** when the spread falls below 1 %/yr or inverts. This is a state-based exit, not a fixed holding period.
- **`funding_rate_analysis.py`.** The "futures term structure" is *synthesised* from current and average funding (`_generate_implied_curve`). It is not market data, so calendar-spread results built on it are not evidence.
- **Cost model.** A reasonable structure: maker/taker per venue, sqrt participation impact, funding and roll costs (`VenueCostModel`, `BinanceFuturesCostModel`).

**Quality verdict.**
- Broad scaffolding, partly synthetic inputs, and headline numbers that cannot be reproduced from the code read.
- Not usable as evidence.

**Reusable ideas.**
- **State-based exit** for cross-venue funding (hold while the spread persists, exit on compression or inversion).
- **Venue fee/interval normalisation.**
- **Hyperliquid** as a structurally different venue: on-chain perps, a different user base, hourly funding.

## 4. Gautam-Kanna/crypto-momentum-reversal (commit 8418042)

File: `Crypto_Momentum_Reversal.ipynb` (cells extracted). 10 large coins, 4h bars, 2021–23 train, 2024–25 holdout,
20 bp costs.

**How it works.**
- **Portfolio:** centred rank weights, dollar-neutral (`xs_portfolio`); positions lagged one bar (`backtest`).
- **Horizon scan:** reversal only at the 4h lookback; momentum from 8h to 30d, better when the latest bar is skipped.
- **Conditional tests:** reversal concentrated in low-volume coins; residual (BTC-beta-hedged) variants; weekend split; dispersion regimes.
- **Seasonality:** "same time of day" signal, the mean of the return at the same 4h slot over the last 30 days. Strongest before costs (gross Sharpe 2.94), but it rebuilds the book every bar.
- **Turnover control:** EWM smoothing of the target weights (half-life grid 0–48 bars). The half-life is chosen on train.
- **Combination:** mean-variance weights on train, vol-targeted to 20 %.

**Reported holdout.**
- Net Sharpe 0.41 (alpha t = 0.82, not significant), BTC correlation −0.08.
- The author states it cannot be separated from luck. Consistent with our E2 (momentum) and E31 (reversal net of costs).

**Reusable ideas.**
- **Weight smoothing** as a turnover cut on an existing signal.
- **Skip-latest-bar.**
- **Time-of-day seasonality** as a distinct mechanism: recurring intraday flows.

## 5. Mapping to Lynxion

| Method | Distinct from Lynxion? | Already tested here? | Verdict |
|---|---|---|---|
| Cointegration pairs (repos 1, 2) | no (E33 pairs) | yes: E33 FAIL; repo 2 independently negative | drop |
| XS momentum / reversal (repo 4) | no | E2, E31, E39 | drop |
| **Target-weight smoothing** (repo 4) | cost reduction on F1, not a new edge | no | **test (E54)** |
| **Staggered tranches** (repo 1 "desks") | robustness of F1 | partly: 7-phase averages in E38/E51 | **test as an execution design (E55)** |
| **Cross-venue funding, state-based exit, Hyperliquid** (repo 3) | yes: venue-relative, new venue | E50: Binance–Bybit, fixed 7-day hold, taker costs → FAIL | **test on new data (E56)** |
| Time-of-day seasonality (repo 4) | yes: intraday periodicity | no | low priority: turnover; at best an execution-timing aid |
| Funding term structure (repo 3) | — | — | not testable: synthetic in the repo, no free futures-curve history |

## 6. Proposed experiments (minimal, pre-registerable)

### E54 — Smoothed XS-COMBO targets (cost reduction on F1)

- **Hypothesis.** Replacing each weekly V1 target w_t by 0.5 · w_t + 0.5 · w_{t−1} (one fixed half-step, no grid) cuts turnover by ≥ 25 % and raises net Sharpe in both windows.
- **Why.** F1 pays 4.5–6.7 %/yr in costs (E41). Signal ranks persist week to week, so half of the change is mostly noise.
- **Data.** Lake; frozen V1 machinery; 7 phases paired.
- **Windows.** DEV 2020–24, TEST 2025–26. The second has been read, so a pass leads to a prospective shadow only.
- **Rejection.**
  - Net Sharpe not higher in both windows, or turnover cut < 25 %.
  - Lagging the signal can cost more alpha than it saves; that is the main failure mode.

### E55 — Staggered 7-tranche execution of XS-COMBO

- **Hypothesis.** Seven tranches of 1/7 gross, each rebalanced weekly on a different weekday (one tranche per day), have the same expected return as single-day rebalancing but a lower variance of outcomes across start dates.
  - Measure: the dispersion of rolling 6-month Sharpe across the 7 single-phase books vs the tranche book.
- **Why.** E38 phase luck (holdout Sharpe 0.50–1.77). The live book is one draw.
- **Data.** Lake, existing code: the tranche book equals the 7-phase average.
- **Cost check.** Daily orders are 1/7 the size. Minimum-notional limits on BingX (6 USDT orders; about 80 USDT per name today becomes about 11 USDT) may bind and must be checked.
- **Decision.**
  - If it passes, implementing it changes the live rebalancer schedule, so it is an operator decision.
  - The rebalancer already writes the 7-phase books daily for R28, so a shadow comparison needs no new code.

### E56 — Binance vs Hyperliquid funding spread, state-based exit

- **Hypothesis.** For coins listed on both venues, enter when the annualised funding spread is ≥ 20 %/yr and expected 30-day carry exceeds 2× costs (taker 5 + 2.5 bp, slippage 2 bp per leg). Exit when the spread is < 2 %/yr or inverts.
  - Net yield on 2× notional must be ≥ 8 %/yr in both windows.
- **Why.** E50 found a real, persistent spread between two centralised venues that was too small for a fixed 7-day hold at taker costs.
  - Hyperliquid's on-chain user base and hourly funding plausibly create larger, longer dislocations.
  - A state-based exit amortises costs.
- **Data.** Hyperliquid `info` API `fundingHistory`: free, verified from 2023-06, 235 coins. Binance funding and prices from the lake. Hyperliquid candles via the same API.
- **Windows.** DEV 2023-07..2024-12, TEST 2025–26: new data, never read.
- **Failure modes.** On-chain venue risk; oracle/mark-price basis between venues; capacity on thin Hyperliquid books.
- **Rejection.** Yield below the bar, or worst single-trade basis loss < −5 %.

### Not proposed

- Time-of-day seasonality: high turnover. Revisit only as an execution-timing aid for F1 rebalances, if E55 moves execution to daily tranches.

## 7. Recommended order

1. **E54** (cost on F1, low effort, existing data).
2. **E55** (robustness of F1, existing data and shadow files).
3. **E56** (new venue, new data download).

All three are research only. Any live change remains an operator decision.
