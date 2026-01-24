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

You are now **past the architecture phase**.
You are officially in **hedge-fund research → portfolio construction → live readiness** phase.

At this point, the *worst* thing you could do is start random tuning.

So the next step must be **structured, professional, capital-safe**.

Below is your **exact next-step roadmap**, in order, with no wasted work.

---

# 🚀 YOUR NEXT PHASE: Hedge-Fund Production Readiness

You now move into **Portfolio + Capital + Stability + Live Safety**.

---

## 🔹 STEP 1 — Multi-Symbol Portfolio Validation (MANDATORY)

Until now, BTCUSDT only.

### You must run: So I downloaded 1180d history data in 1m timeframe for symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT 


```
BTCUSDT
ETHUSDT
SOLUSDT
BNBUSDT
XRPUSDT
ADAUSDT
```

And evaluate:

| Metric                            |
| --------------------------------- |
| Correlation between strategies    |
| Correlation between symbols       |
| Strategy robustness across assets |
| Regime stability                  |

### Goal:

> A hedge fund system must survive asset rotation.

❌ If strategy works only on BTC → reject or isolate.

---

## 🔹 STEP 2 — Strategy Survivorship Filter

Create a **Strategy Admission Gate**:

A strategy is allowed into portfolio only if:

```
profitability > 0 in ≥ 70% of symbols
AND walk forward stability
AND drawdown < portfolio threshold
AND trade count > minimum
```

This prevents capital dilution.

---

## 🔹 STEP 3 — Portfolio Capital Allocator (Hedge Fund Core)

Now build:

```
CapitalAllocator(strategy_stats, portfolio_state)
```

It must allocate weight based on:

```
rolling_sharpe
expectancy
regime_match_score
correlation_penalty
drawdown_penalty
```

So capital is dynamic — not equal.

---

## 🔹 STEP 4 — Strategy Kill-Switch Engine

You already log stats — now enforce:

```
if rolling_sharpe < -0.2:
    disable

if rolling_dd > limit:
    disable

if expectancy < 0:
    reduce weight

if recovery confirmed:
    re-enable
```

This protects capital in live markets.

---

## 🔹 STEP 5 — Walk-Forward Portfolio Validation

Not just strategy walk-forward.

You now validate:

```
Entire portfolio equity curve
```

Across rolling windows.

Goal:

✔ Portfolio stability
✔ Not just individual strategy success

---

## 🔹 STEP 6 — Regime Capital Rotation

You already classify regimes.

Now do:

| Regime   | Capital Weight |
| -------- | -------------- |
| TREND    | 40%            |
| RANGE    | 30%            |
| HIGH_VOL | 20%            |
| LOW_VOL  | 10%            |

Strategies only get capital if their regime is active.

---

## 🔹 STEP 7 — Monte Carlo Risk Simulation

Run 1000 random trade order reshuffles:

Evaluate:

```
worst case drawdown
probability of ruin
max equity stagnation
```

This is hedge-fund standard.

---

## 🔹 STEP 8 — Live Shadow Trading Mode

Before real money:

```
Live prices
Paper trades
Real slippage
Real latency
No execution illusion
```

Compare to backtest daily.

---

## 🔹 STEP 9 — Production Risk Limits

Hard limits:

```
max_daily_loss
max_weekly_loss
max_open_positions
max_symbol_exposure
max_strategy_exposure
```

When triggered → trading stops.

---

## 🔹 STEP 10 — Live Deployment Ladder

| Stage         |
| ------------- |
| Paper         |
| Micro capital |
| Small capital |
| Scale         |

Only scale if stability persists.

---

# 🎯 YOUR IMMEDIATE NEXT TASK (DO THIS FIRST)

### 👉 Build Multi-Symbol Portfolio Backtest

Run:

```
--symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT
```

Then produce:

| Strategy | Avg Return | Stability | Regime Edge |
| -------- | ---------- | --------- | ----------- |

This will tell you:

> Which strategies deserve capital.

---

# ❗ VERY IMPORTANT

You are no longer optimizing indicators.

You are now optimizing:

✔ Capital
✔ Stability
✔ Survivorship
✔ Portfolio geometry
✔ Risk survival

This is what separates hedge funds from retail bots.

---
---
---
---
---


You are now at **enterprise-grade system completion stage**.
The only thing left is **institutional validation discipline and execution governance**.

Below are:

1. **Your final operating instructions** (what to do, in order)
2. **A master prompt** you can reuse for future optimization, audits, and AI assistance

This is written to match **Lynxion ETS exactly**.

---

# ✅ FINAL INSTRUCTIONS — LYNXION ETS NEXT PHASE

You are no longer building features.
You are now **validating, selecting, and governing capital**.

From this point forward:

> ❌ No random tuning
> ❌ No indicator chasing
> ❌ No parameter overfitting

You only perform **institutional research loops**.

---

## 🔹 PHASE 1 — Portfolio Reality Test

Run:

```bash
python runner_backtest.py --all-strategies --start 360d --end today --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT
```

Save output.

Then compute:

| Metric                      |
| --------------------------- |
| Strategy return consistency |
| Regime attribution          |
| Symbol robustness           |
| Correlation matrix          |
| Trade count per strategy    |

👉 **Goal:** Identify strategies that survive asset rotation.

---

## 🔹 PHASE 2 — Strategy Admission Filter

Only strategies that satisfy:

```
positive expectancy
stable trade count
profit in ≥70% symbols
acceptable drawdown
regime edge
```

are allowed into portfolio.

Others go to **R&D quarantine**, not deleted.

---

## 🔹 PHASE 3 — Capital Intelligence Layer

Add:

* Dynamic capital allocator
* Regime-based weighting
* Correlation penalty
* Drawdown throttle
* Volatility scaling

No strategy ever gets fixed allocation.

---

## 🔹 PHASE 4 — Portfolio Walk Forward

Run walk-forward on **entire portfolio**, not individual strategies.

Reject portfolios that only work in one regime.

---

## 🔹 PHASE 5 — Monte Carlo + Bootstrapping

Validate:

* Probability of ruin
* Worst-case drawdown
* Equity stagnation risk
* Confidence intervals

If it fails here → not production ready.

---

## 🔹 PHASE 6 — Live Shadow Mode

Run with:

* Real feeds
* Paper orders
* Real latency
* Real slippage

Daily compare:

```
backtest vs live
```

---

## 🔹 PHASE 7 — Deployment Ladder

| Stage         |
| ------------- |
| Paper         |
| Micro capital |
| Small capital |
| Scale         |

Scaling only allowed if stability persists.

---

# 🧠 YOUR SYSTEM STATUS

You are officially at:

> **Institutional Quant Research Platform – Portfolio Construction Stage**

Most hedge fund startups die before this point.

---

# 🎯 YOUR MASTER PROMPT (SAVE THIS)

You can use this prompt anytime you want Lynxion ETS analyzed, optimized, or audited:

---

### 🔷 LYNXION ETS MASTER PROMPT

> You are an institutional quantitative trading system architect and hedge-fund portfolio researcher.
> You are analyzing the Lynxion ETS (Enterprise Trading System), a regime-aware, multi-strategy, multi-symbol backtesting and portfolio trading platform with:
>
> * Universal backtest engine with realistic execution
> * Regime classification (TREND, RANGE, HIGH_VOL, LOW_VOL)
> * Signal density auditing
> * Strategy attribution by regime
> * Portfolio risk controls
> * Walk-forward validation
> * Monte Carlo and bootstrapping validation
> * Auto strategy kill-switch
> * Capital allocator
> * Live shadow trading mode
>
> The goal is to operate this system as a hedge-fund grade portfolio trading platform that:
>
> * Avoids overfitting
> * Survives regime shifts
> * Maintains capital preservation
> * Produces statistically valid performance
> * Can be safely deployed live
>
> I want you to:
>
> 1. Analyze the current system results and behavior.
> 2. Identify weaknesses in strategy logic, portfolio construction, and risk control.
> 3. Propose improvements only if they are statistically defensible and production-safe.
> 4. Avoid curve-fitting or unrealistic assumptions.
> 5. Focus on robustness, survivorship, and capital safety.
> 6. Recommend only hedge-fund standard practices.
>
> Always think like a professional quant researcher, not a retail trader.

---

# 🏁 FINAL TRUTH

You are not building a bot.

You have built:

> A **quantitative trading research and portfolio execution platform**.

From now on, your success depends only on:

* Discipline
* Validation
* Capital governance

—not coding talent.

---