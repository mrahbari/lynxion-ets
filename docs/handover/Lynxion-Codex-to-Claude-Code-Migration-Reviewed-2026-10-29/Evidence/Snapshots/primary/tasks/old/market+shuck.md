
# Research Prompt – Portfolio-Level Shock Protection (Future Phase)

**Role:** Principal Quant Researcher, Portfolio Risk Architect, and Production Trading Systems Auditor.

## Context

The current production trading system has demonstrated stable execution, broker reconciliation, cooldown enforcement, and capital protection. The architecture is considered frozen, and no architectural redesign is allowed.

Recent live observations revealed a recurring portfolio-level risk event:

* Multiple independent LONG positions across different symbols were simultaneously profitable.
* A sudden market-wide selloff (likely news-driven or macro event) caused all positions to reverse together.
* Individual Stop Loss logic functioned correctly.
* However, the portfolio experienced a correlated drawdown because all positions shared the same market direction.

This is **not considered a bug** in the execution engine or strategy logic.

Instead, it is identified as a **Portfolio Risk Management opportunity** for future research.

---

# Objective

Design a **Portfolio-Level Risk Overlay** that operates independently of entry strategies.

The existing strategy logic must remain unchanged.

The objective is to reduce catastrophic correlated losses while preserving profitable trades during normal market conditions.

---

# Research Scope

The research should focus only on the following two mechanisms.

## 1. Portfolio Correlation Protection

Investigate a global portfolio monitoring layer capable of detecting when multiple open positions are exposed to the same market direction.

Examples include:

* Many simultaneous LONG positions
* High correlation with BTC
* High correlation with Total Crypto Market movement
* Concentrated directional exposure
* Market-wide liquidation events

The system should evaluate:

* Number of active positions
* Net portfolio exposure
* Directional concentration
* Correlation between open positions
* BTC dominance over the portfolio
* Aggregate unrealized PnL
* Portfolio drawdown velocity

The goal is to determine whether a global portfolio risk state exists.

---

## 2. Portfolio Emergency Exit (Kill Switch)

When an abnormal market-wide event is detected, evaluate whether the system should temporarily override individual trade management.

Potential research ideas include:

* Close all positions immediately
* Close only positions aligned with the market shock
* Reduce exposure proportionally
* Freeze new entries for a configurable cooldown period
* Trigger only under statistically significant market events

The mechanism should be event-driven rather than time-driven.

---

# Important Constraints

Do NOT:

* Modify strategy signal generation.
* Modify existing entry logic.
* Rewrite existing strategies.
* Change the trading architecture.
* Replace the execution pipeline.
* Introduce speculative redesigns.

The feature must act only as an independent portfolio-level protection layer.

---

# Scientific Requirements

Any proposed mechanism must be supported by:

* Statistical justification
* Historical validation
* Live trading observations
* False-positive analysis
* False-negative analysis
* Expected impact on expectancy
* Impact on profit factor
* Impact on maximum drawdown
* Impact on recovery factor

No heuristic should be accepted without empirical evidence.

---

# Validation Requirements

Before implementation, provide:

1. Quantitative rationale.
2. Expected benefits.
3. Possible disadvantages.
4. Failure scenarios.
5. False trigger scenarios.
6. Metrics required for evaluation.
7. Backtesting methodology.
8. Walk-Forward validation methodology.
9. Live shadow-mode validation plan.
10. Production rollout strategy.

---

# Success Criteria

The proposal should aim to:

* Reduce catastrophic correlated portfolio losses.
* Preserve existing strategy edge.
* Minimize unnecessary emergency exits.
* Avoid increasing false exits.
* Remain fully compatible with the existing production architecture.

---

## Research Status

**Status:** Future Research Only

**Implementation:** NOT AUTHORIZED

**Priority:** After collecting a statistically significant live sample (minimum several hundred completed trades) and after completing the currently planned improvements (SL/TP refinement, trade management, and execution enhancements).




---

# Research Backlog – Portfolio Correlation & Market Event Risk Protection (Future Phase)

## Status

**Research Only – Deferred**

Do NOT implement this now.

This is a future research track that must only begin after the current high-priority trading issues have been completed, validated, and statistically verified.

---

# Current Priority (Must Be Completed First)

The following work remains the highest priority because it directly impacts profitability and trade quality:

1. **Stop Loss redesign**

    * Structural stop placement
    * ATR-aware adaptive stops
    * Liquidity sweep protection
    * Avoid obvious stop locations

2. **Take Profit redesign**

    * Structure-aware TP
    * Dynamic R:R validation
    * Multi-stage TP (TP1 / TP2)

3. **Trailing Stop implementation**

    * Break-even transition
    * ATR trailing
    * Profit protection
    * Partial position management

4. **Entry Quality Improvements**

    * HTF trend filters
    * Momentum filters
    * Candle confirmation
    * Resistance/support awareness

5. **Confidence Calibration**

    * Investigate why confidence is clustered around identical values.
    * Verify confidence calculation from raw watcher signals through Fusion and Strategy layers.
    * Ensure confidence represents real statistical edge.

6. **Execution Consistency**

    * Verify Telegram entry price vs broker execution price.
    * Verify SL/TP calculations.
    * Verify first trade timestamps.
    * Investigate long periods without new trades after startup.
    * Continue improving live execution reliability.

These items remain the primary objective before introducing additional portfolio-level intelligence.

---

# Future Research Track

## Portfolio Correlation & Market Event Protection

### Objective

Protect the portfolio from catastrophic market-wide events where many independent positions become highly correlated and are stopped out simultaneously.

This is a portfolio-level risk management layer.

It must wrap the existing architecture.

It must NOT modify:

* Watchers
* Fusion
* Strategies
* Signal generation
* Entry logic

Instead, it operates immediately before execution.

---

## Research Questions

Determine whether the system should temporarily reduce or stop new exposure when:

* Multiple open positions become highly correlated.
* The entire crypto market moves sharply in one direction.
* BTC experiences an abnormal volatility expansion.
* A market-wide liquidation cascade begins.
* News-driven panic affects nearly every symbol simultaneously.

---

## Candidate Protection Mechanisms

### 1. Portfolio Correlation Guard (Highest Priority)

Measure real-time correlation across active positions.

Examples:

* Too many LONG positions with similar beta.
* Too many positions moving almost identically.
* Excessive directional concentration.

Possible actions:

* Reject additional correlated trades.
* Reduce position sizing.
* Pause new entries temporarily.

---

### 2. Market Shock / Systemic Risk Detector

Research a portfolio-wide emergency brake using signals such as:

* BTC volatility expansion
* Market-wide ATR explosion
* Funding changes
* Liquidation spikes
* Cross-market momentum bursts
* Sudden correlation increase

Possible actions:

* Freeze new entries for a configurable time window.
* Allow only exits and risk reduction.
* Resume trading automatically once conditions normalize.

---

## Validation Requirements

This research must NOT rely on intuition.

Implementation may only be considered after collecting sufficient live production evidence.

Minimum requirements:

* At least 300–500 completed live trades.
* Multiple market regimes.
* Trending markets.
* Range markets.
* High-volatility sessions.
* News-driven crashes.
* Liquidation events.

Only after statistical analysis demonstrates a measurable improvement should any implementation be proposed.

---

## Architectural Constraints

Any future implementation must:

* Preserve the existing architecture.
* Avoid introducing unnecessary managers or services.
* Minimize code changes.
* Integrate cleanly into the existing execution/risk layer.
* Remain fully testable.
* Be production-safe.
* Be supported by quantitative evidence rather than assumptions.

---

## Expected Outcome

The objective is **not** to increase the number of winning trades.

The objective is to reduce catastrophic portfolio losses during rare market-wide events while preserving the system's normal behavior during healthy market conditions.

This research track is intentionally deferred until the current execution, stop-loss, take-profit, trailing-stop, and entry-quality improvements have been fully completed and validated.
