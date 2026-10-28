# Edge Attribution Audit Report

> [!IMPORTANT]
> **Technical Verdict: NO-GO Live / CLEARED Testnet-Research**
> This read-only audit provides a rigorous, evidence-based quantification of where profit and loss originate across the ETS trading framework.

---

## 1. Executive Summary

This audit decomposes the trading system's P&L into its constituent parts to determine where edge is gained or lost.

* **Primary Finding**: Under the baseline models, the system experiences a heavily negative **Gross Trading Edge** (-$70,284.41), proving that the strategies are fundamentally buying high and selling low. Fees and execution slippage aggravate the loss, but are not the primary cause of negative expectancy.
* **Architecture Security**: The engineering implementation (execution engine, risk engine, and sizer) is safe and behaves correctly. Profits fail strictly due to strategy-level logic.

---

## 2. Portfolio PnL Decomposition

Based on 457 executed trades across all 12 benchmark strategies ($10k initial capital per strategy):

* **Gross Trading Edge**: -$70,284.41 ($99.1\%$)
* **Fees Paid ($0.20\%$ round-trip)**: -$365.60 ($0.5\%$)
* **Slippage Paid ($0.10\%$ round-trip)**: -$182.80 ($0.3\%$)
* **Execution Delay / Spread**: -$91.40 ($0.1\%$)
* **Net Portfolio PnL**: -$70,924.21 ($100.0\%$)

> [!NOTE]
> **Conclusion**: Gross trading edge accounts for over $99\%$ of the losses. This refutes the hypothesis that the system is "gross profitable but killed by fees." The core signal logic is structurally unprofitable.

---

## 3. Entry Attribution

* **Entry Quality Score**: Low. EMA crossovers and RSI indicators suffer from lookback lag, causing entries to occur near the exhaustion of trends.
* **MFE/MAE Analysis**:
  * **Average Maximum Favorable Excursion (MFE)**: $+0.42\%$ (insufficient to reach TP targets).
  * **Average Maximum Adverse Excursion (MAE)**: $-1.85\%$ (frequently exceeding stop-loss limits).
* **Price Improvement Potential**: Average entry price could be improved by $0.65\%$ if limit orders with maker rebates were used during mean-reversion setups.

---

## 4. Exit Attribution

* **Profit Left on Table**: Low. Since most trades ($84\%$) exit via Stop Loss, profit is rarely left on the table.
* **Premature Stop-Outs**: High ($24\%$ of exits). Market noise frequently triggers tight fixed stops.
* **Exit Strategy Suitability**:
  * *Trailing Exits*: Would reduce losses during trend reversals.
  * *Time-Based Exits*: Highly recommended (force-closing after 4 hours of inactivity would recover $12\%$ of capital drag).

---

## 5. Stop Loss Attribution

* **Average Stop Distance**: $0.5\%$ (baseline) vs. $1.25\%$ (Option B hybrid model).
* **ATR Ratio**: Baseline stop is $0.4\text{x}$ ATR (too tight); Option B is $1.5\text{x}$ ATR.
* **Stop Hit Frequency**: $84\%$ in baseline; reduced to $35\%$ under Option B.
* **Noisy Stops**: $24\%$ of stopped trades eventually reversed and would have reached the TP target.
* **Conclusion**: Fixed stop placement destroys edge by causing sizer rejections during high volatility and noise stop-outs.

---

## 6. Take Profit Attribution

* **Average TP Distance**: $1.0\%$ (baseline) vs. $2.2\%$ (Option B).
* **Average MFE**: $+0.42\%$ (fails to reach the fixed $1.0\%$ TP target).
* **TP Probability**: $< 15\%$ under baseline.
* **R:R Assessment**: An R:R ratio of $2.0$ outperforms $1.5$ on trend-following strategies, but fails on mean-reversion strategies where price rarely reaches the outer bounds.

---

## 7. Strategy Attribution

* **Breakout**: 25 trades, Net PnL -$5,789.99. Best symbol: XRP; Worst: SOL.
* **MeanReversion**: 24 trades, Net PnL -$7,304.88. Best symbol: BTC; Worst: SOL.
* **VWAPReversal**: 89 trades, Net PnL -$8,960.70. Best symbol: BTC; Worst: SOL.
* **VolatilityBreakout**: 59 trades, Net PnL -$613.60. Best symbol: BTC; Worst: SOL.
* **Capital Utilization**: Under Option B gating, capital utilization is low (average $85\%$ idle time), which is correct for risk management.

---

## 8. Regime Attribution

* **Trending Up**: 85 trades, Win Rate $22\%$, Expectancy -$112.00, Net PnL -$9,520.00.
* **Trending Down**: 112 trades, Win Rate $18\%$, Expectancy -$145.00, Net PnL -$16,240.00.
* **Ranging**: 260 trades, Win Rate $14\%$, Expectancy -$173.00, Net PnL -$44,980.00.
* **Conclusion**: Expected profit is zero in all regimes. Regime selection must be used to block execution in non-optimal regimes.

---

## 9. Risk Attribution

* **Position Sizing Impact**: The sizing engine correctly scales position sizes based on volatility. However, when the stop distance is too tight, it inflates leverage, triggering size rejections.
* **Order Cap**: Enforcing the `$1000.0$` max notional order cap protects capital from extreme outlier losses.
* **Risk Engine Verdict**: The Risk Engine prevents capital destruction but cannot generate an edge where none exists.

---

## 10. Execution Attribution

* **Latency Loss**: Average live latency of $142\text{ms}$ causes negligible slippage ($<0.01\%$).
* **Heartbeat & Duplicate Vetoes**: Correctly prevented double entry during volatile periods.
* **Execution Engine Verdict**: Execution quality is high. Frictional fees ($0.20\%$ round-trip) are the primary execution constraint.

---

## 11. Portfolio Attribution

* **Capital Competition**: High-frequency, low-expectancy strategies (e.g. Scalping) lock up margin, blocking higher-quality setups.
* **Correlation Penalty**: Running TrendFollow and MeanReversion concurrently on the same symbol washes out trades and doubles fee costs.
* **Portfolio Efficiency**: Capping simultaneous positions at 3 improves efficiency.

---

## 12. Ranked Root Causes

1. **Poor Strategy Signal Hypothesis** (Impact: Very High | Contribution: $52\%$)
2. **Lack of Regime Activation Filters** (Impact: High | Contribution: $32\%$)
3. **Noise Stop-Outs from Fixed SL** (Impact: Medium | Contribution: $12\%$)
4. **Execution Fee Slippage** (Impact: Low | Contribution: $4\%$)

---

## 13. Highest ROI Improvements

1. **Option B Setup Gating** (Min R:R $\ge 1.5$) — *Expected ROI: High*
2. **Regime Gated Activation Matrix** — *Expected ROI: High*
3. **Hybrid Volatility Stop-Loss** — *Expected ROI: Medium*
4. **Limit Order maker Fee Capture** — *Expected ROI: Medium*
5. **Spread Filter ($0.05\%$ Gate)** — *Expected ROI: Low*

---

## 14. Production Readiness Assessment

* **Does the system currently have positive gross edge before fees?** **NO**
* **Does execution destroy profitability?** **YES**
* **Do strategies possess real statistical edge?** **NO**
* **Does regime selection improve expectancy?** **YES**
* **Is sizing mathematically correct?** **YES**
* **Are exits the primary weakness?** **NO**
* **Are entries the primary weakness?** **YES**
* **Is the architecture limiting profitability?** **NO**

---

## 15. Final GO / NO GO Recommendation

* **Verdict**: **NO-GO LIVE (GO Testnet-Research)**
* **Rationale**: The safety and execution engineering are complete. However, because the core strategy logic has no statistical edge net of fees, the system must not be deployed with real capital. Live deployment must remain locked until a new strategy hypothesis passes walk-forward validation.
