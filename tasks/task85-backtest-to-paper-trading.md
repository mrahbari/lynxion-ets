- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Readme the ./README.md file to understand the runners, system features and a brief about it!
- 

# 🎯 Final Objective

Build a **robust, multi-strategy hedge-fund grade trading system** that:
✔ Avoids overfitting
✔ Passes out-of-sample and walk-forward
✔ Has central risk control
✔ Works across multiple symbols
✔ Can be safely launched live
✔ Can automatically disable failing strategies

---

# PHASE 1 — Professional Data Preparation

You already have:
> M1 real history → build higher TFs

This is **correct and professional**.

Now enforce:

### Data Cleaning
* Remove duplicates
* Remove broken candles
* Ensure timestamp alignment
* Validate OHLC logic

### TF Construction

Always generate:

```
M1 → M5 → M15 → M30 → H1 → H4
```

Never mix brokers or sources.

### Dataset Split

```
Train: 60%
Validation: 20%
Test: 20%
```

Purpose:

| Segment    | Usage                    |
| ---------- | ------------------------ |
| Train      | Hyperopt                 |
| Validation | Parameter selection      |
| Test       | Final unseen report only |

⚠ Test data must NEVER be touched by hyperopt.

---

# PHASE 2 — Hedge-Fund Grade Backtest Engine

Your backtest must simulate:

✔ Spread
✔ Slippage
✔ Commission
✔ Dynamic position size
✔ Equity tracking
✔ Trade lifecycle

Your report must output:

```python
{
  net_profit,
  profit_factor,
  sharpe_ratio,
  expectancy,
  max_drawdown,
  win_rate,
  trades,
  avg_r_multiple,
  equity_curve
}
```

If any of these is missing → your backtest is NOT professional.

---

# PHASE 3 — Professional Hyperopt (Not Amateur Style)

### Parameter Space Design

Group logically:

```python
indicator_params
risk_params
filter_params
exit_params
```

### Objective Function

Never optimize only profit.

Example:

```python
score = (profit_factor * sharpe) / max_drawdown
```

Or:

```python
score = expectancy - drawdown_penalty
```

### Hard Constraints

Reject solutions if:

```
max_dd > 20%
trades < 300
win_rate < 45%
profit_factor < 1.3
```

### Output

Do NOT keep only best result.

Keep:

```
Top 30–50 stable parameter sets
```

---

# PHASE 4 — Stability & Robustness Filtering

Each top parameter set must survive:

| Test                      | Purpose           |
| ------------------------- | ----------------- |
| Spread x2                 | Cost robustness   |
| Random slippage           | Execution realism |
| Noise candles             | Overfit detection |
| TF shift                  | Time stability    |
| Monte Carlo trade shuffle | Equity stability  |

Only survivors move forward.

---

# PHASE 5 — Walk Forward Analysis

Example:

| Window | Train   | Test |
| ------ | ------- | ---- |
| WF1    | 2022    | 2023 |
| WF2    | 2022–23 | 2024 |
| WF3    | 2023    | 2024 |

Strategy must perform consistently in all.

Fail once → discard.

---

# PHASE 6 — Multi-Strategy Portfolio

Each strategy must provide:

* Equity curve
* Drawdown
* Return
* Correlation

Portfolio rules:

✔ Correlation < 0.5
✔ Portfolio DD < Individual DD
✔ Equity smoother

---

# PHASE 7 — Central Risk Engine

Global rules:

```
Max daily DD
Max weekly DD
Max risk per strategy
Max risk per symbol
Max open positions
Kill switch
```

Dynamic risk:

```python
risk = base_risk * performance_factor
```

---

# PHASE 8 — Real Paper Trading

Minimum:

🕒 2–4 weeks

Track:

* Backtest vs Live difference
* Slippage
* Spread behavior
* Execution delay
* Equity deviation

---

# PHASE 9 — Live Capital Scaling

| Stage  | Risk  |
| ------ | ----- |
| Micro  | 0.25% |
| Small  | 0.5%  |
| Normal | 1%    |

Scale only if live metrics ≈ backtest metrics.

---

# PHASE 10 — Auto Strategy Monitoring

Each strategy must be stopped if:

```
Live DD > Backtest DD × 1.5
Win rate drops
Expectancy turns negative
```

---

# Professional Architecture is already implemented, just annals to understand and use it!

---

# 🚀 FINAL MASTER ADVANCED PROMPT

You can use this prompt in any AI or development environment to drive this project:

---

## 🔥 HEDGE FUND SYSTEM MASTER PROMPT

> I am building a hedge-fund grade multi-strategy algorithmic trading system.
> I already have real M1 historical data and I generate all higher timeframes from it.
> I want to implement a full professional pipeline including:
>
> * Institutional grade backtesting with spread, slippage, commission and dynamic risk
> * Hyperopt with stability constraints and multi-metric objective function
> * Walk-forward analysis
> * Robustness and stress testing
> * Multi-strategy portfolio construction with correlation filtering
> * Centralized risk management engine
> * Paper trading validation
> * Controlled live deployment with scaling rules
>
> The system must avoid overfitting, be statistically robust, and suitable for real capital deployment.
>
> I want all designs, code, logic, and architecture to follow professional hedge-fund and quantitative trading standards.
>
> Do NOT rewrite my entire system. Improve and extend my existing structure only.
>
> Always prioritize:
>
> * Robustness over profit
> * Stability over optimization
> * Risk control over return
>
> Now guide me step-by-step through implementing this system in production-grade quality.

---
