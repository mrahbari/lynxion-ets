# Research Iteration 02: VWAP Band Deviation & Passive Limit Order Execution

> **Role**: Principal Quant Researcher & Technical Lead  
> **Status**: COMPLETED (DISCARDED)  
> **Target Strategies**: `mean_reversion`, `vwap_reversal`

---

## 1. Hypothesis Tested
Mean-reversion market orders suffer from taker fee drag ($0.10\%$ per leg). Executing entries via passive limit orders at the outer VWAP 2.0 Standard Deviation Band captures maker fee rebates ($-0.02\%$ fee) and eliminates entry slippage ($0.05\% \rightarrow 0.00\%$), recovering $+0.24\%$ net expectancy per trade.

---

## 2. Implementation & Parameters
* **Strategy Logic**: Modified `VWAPReversalStrategyAdapter` setup engine to issue passive limit order intents at the 2nd VWAP band.
* **Parameters**:
  * `VWAP_BAND_MULTIPLIER` = 2.0
  * `RSI_OVERSOLD` = 30
  * `EXECUTION_TYPE` = Limit Order (Maker Rebate -0.02%)
  * `FEE_ROUNDTRIP` = 0.06% (Maker Entry -0.02% + Taker Exit 0.08%)

---

## 3. Backtest & Walk-Forward Validation
Evaluated across BTCUSDT, ETHUSDT, and SOLUSDT over 4 sequential 3-month Walk-Forward OOS folds ($S_1$ to $S_4$):

| Asset | Total Trades | Win Rate | Gross Expectancy | Net Expectancy (-0.06% fee) | Positive Folds (WFO) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BTCUSDT** | 42 | 42.8% | +0.03% | -0.03% | 2 / 4 |
| **ETHUSDT** | 38 | 39.5% | +0.01% | -0.05% | 1 / 4 |
| **SOLUSDT** | 55 | 29.1% | -0.32% | -0.38% | 0 / 4 |

---

## 4. Statistical Evidence & Confidence Intervals
* **95% Confidence Interval for Net Expectancy (BTCUSDT)**: $[-0.18\%, +0.12\%]$. Includes zero, confirming lack of statistical significance.
* **Max Drawdown**: $-14.2\%$
* **Profit Factor**: $0.94$ (BTCUSDT) / $0.45$ (SOLUSDT)

---

## 5. Failure Diagnosis & Weaknesses
1. **Adverse Selection / Fill Risk**: Limit orders at the outer VWAP band suffered from adverse selection: orders were filled primarily when price was experiencing strong trend expansion (breaking through the band), leading to large trend-continuation losses.
2. **Cross-Symbol Failure**: Performance collapsed on SOLUSDT (0/4 positive folds), proving that the maker rebate edge is not cross-symbol stable.

---

## 6. Verdict & Next Experiment
* **Verdict**: **DISCARDED** (Fails out-of-sample WFO persistence and exhibits severe adverse selection).
* **Next Experiment**: Evaluate non-OHLCV derivatives data interaction (Extreme Funding Rate Capitulation + Order Flow CVD Surge) in Iteration 03.
