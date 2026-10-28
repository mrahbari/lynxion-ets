You are acting as a Senior Quant Engineer, Trading System Auditor, and Python Architect.

Your task is NOT to optimize profitability yet.

Your primary objective is to investigate why only one strategy (`trend_following`) is producing trading signals while every other strategy appears to be inactive.

This is a production-grade multi-strategy algorithmic trading system with the following architecture:

Market Data
↓
Watchers
↓
Regime Engine
↓
Fusion Engine
↓
Strategies
↓
Risk Management
↓
Execution
↓
Broker

The system is designed so that multiple strategies should naturally become active depending on market conditions.

However, in practice almost every generated signal comes from:

- trend_following

while strategies such as (for example)

- breakout
- mean_reversion
- liquidity
- vwap_reversal
- sweep_scalper
- oi_footprint
- crypto_breakout
- mtf_trend

either never generate signals or generate so few that they are effectively disabled.

I want you to perform a complete root-cause investigation.

## Priority 1 (Highest)

Determine WHY the other strategies are not participating.

Investigate every possible cause, including but not limited to:

### Strategy Registration

- Are all strategies actually loaded?
- Are they instantiated correctly?
- Are they enabled in configuration?
- Are they registered inside the engine?
- Is there any filtering before execution?

### Execution Flow

Verify that every strategy is actually called.

Produce evidence such as:

Strategy X
↓

calculate()
↓

signal generated?
↓

filtered?
↓

confidence assigned?
↓

Fusion?
↓

Risk?
↓

Execution?

Locate exactly where each strategy stops contributing.

### Data Availability

Check whether strategies receive all required inputs.

Examples:

- indicators
- higher timeframe candles
- orderflow
- liquidity
- funding
- open interest
- volatility
- volume profile

Some strategies may silently fail because required features are unavailable.

Identify all missing inputs.

### Conditions Too Strict

Inspect every strategy's entry conditions.

Determine whether they are unrealistically restrictive.

Examples:

- multiple confirmations
- ATR filters
- RSI ranges
- trend filters
- volatility filters
- time filters
- liquidity filters

Measure how often each condition rejects trades.

Do not simply state they are "strict".

Quantify:

- rejection rate
- dominant rejection reason
- percentage of rejected opportunities

### Silent Failures

Search for:

- swallowed exceptions
- early returns
- default False conditions
- invalid indicator values
- NaN propagation
- empty datasets
- missing features
- disabled code paths

### Fusion Bias

Inspect the Fusion Engine.

Determine whether:

- one strategy always dominates
- weights suppress other strategies
- confidence normalization is biased
- score clipping removes signals
- voting logic favors trend_following

Verify that Fusion is not unintentionally suppressing other strategies.

### Regime Engine

Check whether the Regime Engine activates only trend-following friendly environments.

Determine:
- detected market regimes
- percentage of time in each regime
- strategy eligibility per regime

### Risk Layer

Determine whether strategies produce signals but are rejected later.

Examples:
- confidence
- position sizing
- exposure limits
- cooldown
- duplicate position
- correlation filter
- risk validation

Provide statistics.

### Logging

If logging is insufficient, specify exactly where diagnostic logs should be added.
The goal is to make future debugging trivial.

---

## Priority 2

I suspect that my recent testing changes reduced the quality of generated trades.
Previously I intentionally lowered several thresholds to increase trade frequency.

Examples include:
- confidence thresholds
- sensitivity
- signal acceptance
- filtering

The result is:
- more trades with different strategies and more precise
- but noticeably lower trade quality

Investigate whether these relaxed thresholds are degrading overall signal quality.

Specifically determine:
- which thresholds were modified
- how much they affect precision
- false positive rate
- signal quality
- trade expectancy

If appropriate, recommend production-grade default values.

Do NOT simply recommend increasing thresholds.

Support every recommendation with reasoning.

---

## Required Deliverables

Produce a structured report with:

### 1. Root Cause Summary

List the exact reasons why non-trend strategies are inactive.

Rank by severity.

---

### 2. Strategy Activity Report

For every strategy include:

- loaded
- executed
- generates raw signals
- filtered before Fusion
- filtered inside Fusion
- rejected by Risk
- final execution count

---

### 3. Signal Funnel

For every strategy show:

Raw Opportunities
↓
Signals Generated
↓
Passed Validation
↓
Passed Fusion
↓
Passed Risk
↓
Executed Trades

Include counts.

---

### 4. Configuration Audit

Identify:

- suspicious parameters
- disabled features
- unrealistic defaults
- threshold problems
- conflicting settings

---

### 5. Code Defects

List every discovered bug or design flaw.

Classify each as:

Critical
High
Medium
Low

---

### 6. Recommended Fixes

Prioritize fixes in execution order.

For each fix include:

- root cause
- affected modules
- expected impact
- implementation complexity

---

IMPORTANT

Do NOT assume that the issue is market conditions.
Assume there is a software, configuration, architectural, or logical cause until proven otherwise.
Base every conclusion on evidence from the code, configuration, runtime flow, logs, and collected statistics.
Do not stop after finding one issue.
Continue until you can explain, with evidence, why the entire multi-strategy system behaves like a single-strategy system.