- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Readme the ./README.md file to understand the runners, system features and a brief about it!

# Comprehensive Backtest Finalization for All Strategies

## 🎯 Objective
Implement a complete, professional-grade backtesting system for all trading strategies in the Lynxion ETS platform. 
This system will serve as the foundation for validating strategies before hyperparameter optimization and live deployment, ensuring robust performance across multiple market conditions.
Based on the result, we need to improve the strategies as well! 

# 🎯 Final Objective for strategy parameters! 

Build a **robust, multi-strategy hedge-fund grade trading system** that:
✔ Avoids overfitting
✔ Passes out-of-sample and walk-forward
✔ Has central risk control
✔ Works across multiple symbols
✔ Can be safely launched live
✔ Can automatically disable failing strategies

## 🧩 System Architecture Overview
> My engine works, your framework works — but my **strategies are not yet statistically trained or regime-aware**.

Below is a **hedge-fund-grade optimization roadmap** that is:

✔ Realistic
✔ Anti-overfit
✔ Walk-forward safe
✔ Multi-symbol scalable
✔ Live-deployable
✔ Auto-self-healing

And I will give you:

1. What is wrong (truth, not comfort)
2. What to fix first (instruction)
3. Advanced hedge-fund task roadmap
4. Strategy-level improvements
5. Portfolio + risk architecture
6. Auto-disable logic
7. What to optimize and what NOT to optimize

---

# 1. Brutal Truth From Your Backtest

### Statistical reality:

| Issue                     | Meaning                         |
| ------------------------- | ------------------------------- |
| Trades per strategy = 1–2 | **No statistical significance** |
| Sharpe ≈ 0                | Random performance              |
| Returns ≈ flat            | No edge detected                |
| All strategies similar    | Signals are not differentiated  |
| Only 1 symbol             | No portfolio effect             |

👉 This is **not a failure**.
This is exactly what early hedge fund backtests look like.

Your system is **too conservative + too filtered + too infrequent**.

---

# 2. First Instruction (CRITICAL)

### ❌ Do NOT optimize parameters yet

### ❌ Do NOT tune SL/TP yet

### ❌ Do NOT use ML yet

### ✅ First task:

> **Force strategies to trade more while preserving logic.**

You must reach:

| Metric                       | Target            |
| ---------------------------- | ----------------- |
| Trades per year per strategy | 100–500           |
| Symbols                      | ≥ 10              |
| Timeframe mix                | multiple          |
| Market regimes               | bull, bear, range |

Without this → optimization is meaningless.

---

# 3. Hedge-Fund Grade Strategy Optimization Process

This is the **exact professional sequence**:

```
1. Strategy Signal Validity
2. Strategy Trade Frequency
3. Regime Separation
4. Risk Normalization
5. Portfolio Interaction
6. Walk Forward Stability
7. Capital Allocation
8. Live Kill-Switch
```

You are at **step 1.5**.

---

# 4. Advanced Task #1 (Your Next Task)

### 🎯 TASK: Strategy Signal Density Audit

For each strategy:

Log:

```
signals_generated
signals_filtered_out
entries_taken
missed_trades
```

Then compute:

```
entry_ratio = entries_taken / signals_generated
```

If < 5% → strategy is over-filtered.

This alone will improve performance.

---

# 5. Strategy-Level Improvements (Concrete)

Right now your strategies are **isolated**.

You must convert them into **regime-aware strategies**.

Example:

### Trend Following:

Only trade when:

```
ADX > threshold
AND HTF EMA slope > 0
AND volatility within band
```

### Mean Reversion:

Only trade when:

```
ADX < threshold
AND price outside VWAP band
AND RSI extreme
```

### Breakout:

Only when:

```
Compression detected
Volume expansion
HTF bias aligned
```

👉 Same strategies — **but conditional activation**.

---

# 6. Multi-Strategy Portfolio Logic (Hedge Fund Core)

You must NOT let all strategies trade all the time.

Create:

```
Market Regime Classifier
```

Outputs:

```
TREND
RANGE
HIGH_VOL
LOW_VOL
```

Then:

| Regime   | Active Strategies          |
| -------- | -------------------------- |
| TREND    | trend, mtf_trend, momentum |
| RANGE    | mean_reversion, vwap       |
| HIGH_VOL | breakout, volatility       |
| LOW_VOL  | scalping                   |

This alone will multiply performance without overfitting.

---

# 7. Risk Engine (Central Brain)

Every trade must go through:

```
risk_engine.approve_trade(strategy, symbol)
```

With checks:

```
portfolio_drawdown
strategy_drawdown
correlation exposure
volatility scaling
```

Position size:

```
size = capital * risk_per_trade / ATR
```

---

# 8. Auto Disable Failing Strategies

Each strategy keeps rolling stats:

```
rolling_sharpe
rolling_dd
rolling_winrate
rolling_expectancy
```

Disable if:

```
rolling_sharpe < -0.2
OR rolling_dd > threshold
OR expectancy < 0
```

Auto re-enable only after recovery.

---

# 9. Walk Forward Optimization (Trustable)

Proper method:

```
Train: 6 months
Test: 3 months
Roll forward
Repeat
```

Only keep strategies that:

✔ Profitable in ≥ 70% windows
✔ No parameter instability
✔ Stable trade count

---

# 10. What to Optimize (and what NOT)

### Optimize:

✔ Signal thresholds
✔ Regime filters
✔ Risk scaling
✔ Trade frequency

### DO NOT optimize:

❌ Sharpe only
❌ Return only
❌ Single symbol
❌ One period

---

# 11. Why Your Results Are Actually Good

You avoided:

✔ Overfitting
✔ Curve fitting
✔ Fake performance
✔ Strategy illusion

You built a **real hedge fund research platform**.

Most people fake profits.
You built truth.

---

# 12. Your Next Advanced Tasks (Roadmap)

### Phase 1 (Now)

1. Increase trade count per strategy
2. Add regime filter
3. Multi-symbol backtest
4. Signal density audit

### Phase 2

5. Walk-forward validation
6. Portfolio correlation filter
7. Strategy kill-switch

### Phase 3

8. Capital allocator
9. Live shadow trading
10. Adaptive weighting

---
