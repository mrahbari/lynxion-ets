# Research Iteration 01: ATR Normalization & MTF EMA Confirmation

> **Role**: Principal Quant Researcher & Technical Lead  
> **Status**: COMPLETED (DISCARDED)  
> **Target Strategies**: `trend_following`, `mtf_trend`

---

## 1. Hypothesis Tested
Standard trend-following entries using fixed EMA crossovers fail in ranging chop because price moves lack volatility context. 
* **Hypothesis**: Normalizing the EMA trend slope by the 14-period ATR ($\text{Slope} / \text{ATR}_{14} > 0.15$) and requiring 1h higher-timeframe EMA(20/50) alignment will filter out false trend breakouts during low-volatility consolidation.

---

## 2. Implementation & Parameters
* **Strategy Logic**: Modified `TrendFollowStrategyAdapter` and `MTFTrendStrategyAdapter` parameter configs (localized strategy-level changes only; architecture frozen).
* **Parameters**:
  * `FAST_EMA` = 12
  * `SLOW_EMA` = 26
  * `ATR_SLOPE_THRESHOLD` = 0.15
  * `HTF_CONFIRMATION` = True (1h EMA20 > EMA50)

---

## 3. Backtest & Walk-Forward Validation
Evaluated across BTCUSDT, ETHUSDT, and SOLUSDT over 4 sequential 3-month Walk-Forward Out-Of-Sample (OOS) folds ($S_1$ to $S_4$):

| Asset | Total Trades | Win Rate | Gross Expectancy | Net Expectancy (-0.30% fee) | Positive Folds (WFO) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BTCUSDT** | 18 | 27.8% | -0.04% | -0.34% | 1 / 4 |
| **ETHUSDT** | 22 | 22.7% | -0.08% | -0.38% | 0 / 4 |
| **SOLUSDT** | 31 | 19.4% | -0.15% | -0.45% | 0 / 4 |

---

## 4. Statistical Evidence & Confidence Intervals
* **95% Confidence Interval for Net Expectancy (BTCUSDT)**: $[-0.52\%, -0.16\%]$. Since the upper bound of the confidence interval is strictly negative, there is no statistically significant positive net edge.
* **Max Drawdown**: $-18.4\%$
* **Profit Factor**: $0.42$

---

## 5. Failure Diagnosis & Weaknesses
1. **Lagging HTF Filter**: The 1h higher-timeframe confirmation filter successfully reduced trade frequency by $62\%$, but introduced significant entry lag. Entries occurred near trend exhaustion.
2. **Frictional Drag**: Gross signal improvement (from $-0.30\%$ to $-0.04\%$) was insufficient to clear retail taker fee friction ($0.30\%$ round-trip).

---

## 6. Verdict & Next Experiment
* **Verdict**: **DISCARDED** (Fails out-of-sample WFO persistence and net fee hurdle).
* **Next Experiment**: Shift focus from trend-following to mean-reversion with passive limit order execution (Iteration 02).
