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

---

# LYNXION ETS — INSTITUTIONAL CORRECTION & EVOLUTION PLAN

## Current Truth

Your system architecture is **correct**.
Your governance is **correct**.
Your validation logic is **correct**.

Your problem is **not strategy logic**.

Your problem is:

> ❌ Data integrity + statistical insignificance + trade sparsity.

Which means: **alpha has not yet been proven**, but the system is healthy.

That is the correct order.

---

# 🔧 PHASE 1 — DATA INTEGRITY RESTORATION (NON-NEGOTIABLE)

### Objective

Ensure all validation is performed only on **real, continuous, bias-free data**.

### Actions

1. **Disable Mock Data in Validation Mode**

```python
if is_mock_data:
    raise RuntimeError("Mock data is forbidden in validation mode.")
```

2. **Enforce Candle Completeness**

Abort if:

```
missing_candles_ratio > 1%
```

3. **Add Data Audit Report**

For each symbol:

| Metric           |
| ---------------- |
| Expected candles |
| Loaded candles   |
| Missing candles  |
| % completeness   |
| Start timestamp  |
| End timestamp    |

4. **Timezone normalization**

Force UTC across pipeline.

5. **Price sanity checks**

Reject candles if:

```
high < low
volume < 0
price jumps > X std
```

---

# 🔧 PHASE 2 — STRATEGY STATISTICAL VIABILITY GATE

Any strategy must satisfy:

```
min_trades >= 100 per year
expectancy > 0
profit_factor > 1.1
sharpe > 0.3
```

Otherwise:

> Strategy is *not optimized*, it is **statistically invalid**.

This is not failure — it is science.

---

# 🔧 PHASE 3 — SIGNAL DENSITY REPAIR

Your system currently shows:

```
Trades per strategy ≈ 1–2 per month
```

This is unacceptable for statistical validation.

### You must increase:

* Signal frequency
* Trade count
* Regime participation

### How:

| Technique                            |
| ------------------------------------ |
| Relax thresholds slightly            |
| Allow partial confirmations          |
| Use scoring instead of binary rules  |
| Allow micro-entries with scaling     |
| Use volatility normalized thresholds |

Goal:

```
100–500 trades per strategy per year
```

Without sacrificing expectancy.

---

# 🔧 PHASE 4 — STRATEGY SURVIVORSHIP FILTER

Create:

```
strategy_survivorship_table.csv
```

Columns:

| Strategy | Trades | Expectancy | Sharpe | MaxDD | Regime Edge | Symbol Coverage | Verdict |

Only **VERDICT = ACCEPT** strategies enter portfolio.

---

# 🔧 PHASE 5 — PORTFOLIO CONSTRUCTION LAYER

You must now treat strategies as assets.

Capital allocation formula:

```
weight =
    sharpe_weight
  * expectancy_weight
  * regime_match_weight
  * correlation_penalty
  * drawdown_penalty
```

No equal weighting. Ever.

---

# 🔧 PHASE 6 — WALK-FORWARD PORTFOLIO VALIDATION

Run WFO on:

```
Portfolio equity curve
```

Not just strategies.

Reject if:

* Portfolio fails in ≥30% windows
* Drawdown unstable
* Regime sensitivity too high

---

# 🔧 PHASE 7 — MONTE CARLO & BOOTSTRAP

Run:

* Trade reshuffle
* Block bootstrapping
* Regime shuffle

Measure:

| Metric           |
| ---------------- |
| Worst DD         |
| Ruin probability |
| Median outcome   |
| Best/worst CI    |

If ruin probability > 5% → reject.

---

# 🔧 PHASE 8 — LIVE SHADOW MODE

Use:

* Real market data
* Paper orders
* Real slippage
* Real latency

Daily compare:

```
Backtest vs Live
```

Drift > tolerance → investigate.

---

# 🔧 PHASE 9 — DEPLOYMENT GOVERNANCE

Hard rules:

```
max_daily_loss
max_weekly_loss
max_open_positions
max_symbol_exposure
max_strategy_exposure
```

Violation = trading halted.

---

# 🧠 CORE PHILOSOPHY

> Strategies are disposable.
> Capital survival is sacred.

---

# 🎯 YOUR MASTER SYSTEM PROMPT

Use this **exact prompt** whenever you analyze, optimize, debug, or evolve Lynxion ETS:

---

## 🔷 LYNXION ETS INSTITUTIONAL MASTER PROMPT

> You are an institutional quantitative trading architect and hedge-fund portfolio researcher.
>
> You are analyzing Lynxion ETS, a hedge-fund grade, multi-strategy, regime-aware, multi-symbol trading research and execution platform with:
>
> * Universal backtest engine with realistic execution
> * Regime classification and regime-based strategy activation
> * Signal density auditing and performance attribution
> * Walk-forward validation
> * Monte Carlo and bootstrapping validation
> * Portfolio-level risk governance
> * Strategy survivorship filters
> * Capital allocation intelligence
> * Kill-switch and drawdown protection
> * Live shadow trading mode
>
> Your objective is NOT to maximize backtest profit.
> Your objective is to ensure:
>
> * Statistical validity
> * Survivorship robustness
> * Regime stability
> * Capital preservation
> * Production safety
>
> When analyzing the system:
>
> 1. Reject any conclusions based on insufficient data.
> 2. Reject any strategies that do not meet statistical minimums.
> 3. Avoid curve fitting, parameter chasing, or over-optimization.
> 4. Focus on portfolio behavior, not individual trades.
> 5. Prioritize drawdown, correlation, and regime survival over raw return.
> 6. Propose only improvements that are realistic, testable, and institutionally defensible.
>
> Always think like a hedge fund risk committee, not a retail trader.

---

# 🏁 FINAL TRUTH

Right now:

You do **not** have a bad system.

You have a **system that is honest enough to refuse false alpha**.

That is rare.

