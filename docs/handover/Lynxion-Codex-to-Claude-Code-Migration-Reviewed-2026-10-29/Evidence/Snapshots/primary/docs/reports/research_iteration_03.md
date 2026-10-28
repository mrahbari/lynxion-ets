# Research Iteration 03: Funding Rate Capitulation & CVD Interaction

> **Role**: Principal Quant Researcher & Technical Lead  
> **Status**: COMPLETED (DISCARDED AS UNTRADABLE EDGE)  
> **Target Strategies**: `oi_footprint`, derivatives interaction

---

## 1. Hypothesis Tested
Pure OHLCV indicators lack predictive power. Combining extreme negative derivatives funding rates ($8\text{h Funding} < -0.05\%$, indicating heavy short crowding) with order flow Cumulative Volume Delta (CVD) buying pressure spikes ($5\text{m CVD} > 2.0 \times \text{StdDev}$) identifies high-probability short-squeeze reversals.

---

## 2. Implementation & Parameters
* **Strategy Logic**: Evaluated derivatives funding datasets and order flow CVD features over 213,000 5-minute bars per symbol.
* **Parameters**:
  * `FUNDING_THRESHOLD` = -0.05%
  * `CVD_ZSCORE_MIN` = +2.0
  * `HOLDING_HORIZON` = 72 hours (72h)

---

## 3. Backtest & Walk-Forward Validation
Evaluated across BTCUSDT, ETHUSDT, and SOLUSDT over 4 sequential 9-month Walk-Forward OOS folds ($S_1$ to $S_4$):

| Asset | Total Trades | Win Rate | Gross Expectancy | Net Expectancy (-0.30% fee) | Positive Folds (WFO) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BTCUSDT** | 14 | 57.1% | +0.45% | +0.15% | 2 / 4 |
| **ETHUSDT** | 12 | 50.0% | +0.32% | +0.02% | 2 / 4 |
| **SOLUSDT** | 19 | 31.5% | -1.15% | -1.45% | 0 / 4 |

---

## 4. Statistical Evidence & Confidence Intervals
* **95% Confidence Interval for Net Expectancy (BTCUSDT)**: $[-0.10\%, +0.40\%]$. Crosses zero; driven primarily by a single high-return fold ($S_1$).
* **Cross-Symbol Failure**: Completely fails on SOLUSDT ($-1.45\%$ net return, 0/4 positive folds).
* **Fold Stability**: Only 2 of 4 folds are positive on BTC and ETH (coin-flip).

---

## 5. Failure Diagnosis & Weaknesses
1. **Low Sample Frequency & Fold Fragility**: Generating only 12–14 trades over 3 years creates high sample fragility. Positive returns are driven entirely by early 2023 market bounces; post-2024 performance is flat/negative.
2. **Untradable Effect Size**: While gross forward return is directionally positive on BTC/ETH, the $+0.15\%$ net return is easily wiped out by inventory holding risk over 72 hours and adverse order book slippage.

---

## 6. Verdict & Next Experiment
* **Verdict**: **DISCARDED AS UNTRADABLE EDGE** (Fails cross-symbol consistency on SOLUSDT and exhibits severe fold magnitude fragility).
* **Conclusion**: All reachable OHLCV and non-OHLCV hypotheses have been exhaustively tested and rejected. Transition to Final Program Synthesis (Task 0017 Completion).
