- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md


# 🔹 Logging Prompt — Pre-Forensic Optimization Phase

## Objective

Implement a **forensic-grade structured logging system** across the entire trading architecture to enable post-trade decision reconstruction, bias detection, and institutional-level optimization.

This logging phase is mandatory before any performance optimization, ML integration, or parameter tuning.

---

## Why This Logging Is Required

Without forensic logging:

* Profit or loss cannot be traced to architectural decisions.
* Engine, fusion, and strategy biases remain invisible.
* Optimization becomes speculative and dangerous.
* ML training becomes polluted with unverified decision chains.

With forensic logging:

* Every trade becomes a full decision audit trail.
* Each architectural layer becomes objectively measurable.
* Engine credibility, fusion weights, and strategy selection can be optimized with evidence.

---

## Core Principle

> The system must be able to answer:
> **“Why did this exact trade happen?”**

This requires complete decision traceability across:

```
Watcher → Engine → Fusion → Strategy → Broker → Trade Close
```

---

## Mandatory Logging Design Rules

1. **Structured format (JSON or dict)**
2. **Single shared trade_id across all layers**
3. **Chronological chain integrity**
4. **Layer isolation (no mixed responsibilities)**
5. **No business logic inside logging**
6. **No aggregation inside logging**
7. **No performance shortcuts**
8. **specific log file like "forensic.log" is needed**

---

## Trade Trace ID

A unique trade identifier must be created when Strategy issues an ExecutionIntent:

```python
trade_id = f"{symbol}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
```

This `trade_id` must propagate through all layers.

---

## Logging Responsibilities Per Layer

---

### WATCHER Layer

Purpose: Capture **raw perception of the market**.

Log:

* watcher name
* symbol
* observation type
* observation value
* confidence
* timestamp

Example:

```python
{
  "layer": "WATCHER",
  "watcher": "TrendMTF",
  "symbol": "BTCUSDT",
  "observation_type": "trend_positive",
  "value": 0.0034,
  "confidence": 0.62,
  "timestamp": "2026-01-19T12:01:03.221Z"
}
```

---

### ENGINE Layer

Purpose: Capture **interpretation logic**.

Log:

* engine name
* input observation
* interpreted direction
* confidence
* score

Example:

```python
{
  "layer": "ENGINE",
  "engine": "TrendEngine",
  "symbol": "BTCUSDT",
  "input_observation": "trend_positive",
  "interpreted_signal": "BUY",
  "confidence": 0.58,
  "score": 0.41
}
```

---

### FUSION Layer

Purpose: Capture **collective reasoning**.

Log:

* regime
* fused direction
* confidence
* contributing engines
* weighting logic

Example:

```python
{
  "layer": "FUSION",
  "symbol": "BTCUSDT",
  "regime": "TREND",
  "fused_direction": "BUY",
  "confidence": 0.66,
  "contributors": {
    "TrendEngine": 0.32,
    "OrderFlowEngine": 0.21,
    "VolatilityEngine": 0.13
  }
}
```

---

### STRATEGY Layer

Purpose: Capture **capital deployment decision**.

Log:

* strategy name
* decision
* confidence
* trade_id

Example:

```python
{
  "layer": "STRATEGY",
  "strategy": "TrendFollow",
  "symbol": "BTCUSDT",
  "decision": "BUY",
  "confidence": 0.64,
  "trade_id": "BTCUSDT_20260119120103221"
}
```

---

### BROKER EXECUTION

Purpose: Capture **real execution reality**.

Log:

* trade_id
* side
* execution price
* sl
* tp
* quantity

Example:

```python
{
  "layer": "BROKER",
  "trade_id": "BTCUSDT_20260119120103221",
  "side": "BUY",
  "price": 2034.12,
  "sl": 2029.80,
  "tp": 2043.50,
  "quantity": 1.2
}
```

---

### BROKER CLOSE

Purpose: Capture **truth of the trade**.

Log:

* trade_id
* pnl
* exit reason
* duration

Example:

```python
{
  "layer": "BROKER_CLOSE",
  "trade_id": "BTCUSDT_20260119120103221",
  "pnl": -42.35,
  "exit_reason": "STOP_LOSS",
  "duration_sec": 318
}
```

---

## Why Each Layer Is Logged

| Layer    | Purpose                    |
| -------- | -------------------------- |
| Watcher  | Detect perception bias     |
| Engine   | Detect interpretation bias |
| Fusion   | Detect aggregation bias    |
| Strategy | Detect deployment bias     |
| Broker   | Detect execution bias      |
| Close    | Measure real outcome       |

---

## What This Enables

After logs exist, the system can:

* Reconstruct any trade fully.
* Rank engines by real performance.
* Recalibrate fusion weights.
* Detect strategy regime mismatch.
* Train ML models safely.
* Detect false confidence inflation.
* Perform forensic optimization.

---

## Forbidden Practices

❌ Logging aggregated results only
❌ Logging only winning trades
❌ Logging only strategy layer
❌ Logging without trade_id
❌ Logging text instead of structured data

---

## Success Condition

A single trade must be reconstructed line-by-line from:

```
first market perception → final PnL
```

without any guesswork.

---

## This Phase Name

**Pre-Forensic Instrumentation Phase**

No optimization is allowed before this phase is completed.

---

## What Comes Next

Once this logging is implemented and one real trade is captured, the system is eligible for:

> Hedge Fund Forensic Optimization Phase

Where every architectural layer will be optimized based on evidence, not assumptions.




---
---

# Pre-Forensic Logging Prompt — Crypto Hedge Fund Systems

## Objective

Implement a **forensic-grade structured logging system** across the entire crypto trading architecture to enable post-trade reconstruction, bias detection, and institutional-level optimization.

This logging phase is mandatory before any Hedge Fund Forensic Optimization, ML training, or hyper-parameter tuning.

---

## Core Principle

> The system must be able to answer:
> **“Why did this crypto trade happen?”**

Across:

```
Watcher → Engine → Fusion → Strategy → Broker → Trade Close
```

---

## Trade Trace ID

```python
trade_id = f"{symbol}_{exchange}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
```

Example:

```
BTCUSDT_BINANCE_202601191204338221
```

---

## WATCHER Logging (Crypto)

Purpose: Market perception layer.

```python
{
  "layer": "WATCHER",
  "watcher": "OrderFlowWS",
  "exchange": "BINANCE",
  "symbol": "BTCUSDT",
  "observation_type": "bid_ask_imbalance",
  "value": 1.37,
  "confidence": 0.61,
  "timestamp": "2026-01-19T12:04:33.822Z"
}
```

---

## ENGINE Logging

```python
{
  "layer": "ENGINE",
  "engine": "OrderFlowEngine",
  "symbol": "BTCUSDT",
  "exchange": "BINANCE",
  "interpreted_signal": "BUY",
  "confidence": 0.59,
  "score": 0.44
}
```

---

## FUSION Logging

```python
{
  "layer": "FUSION",
  "symbol": "BTCUSDT",
  "exchange": "BINANCE",
  "regime": "high_vol_trend",
  "fused_direction": "BUY",
  "confidence": 0.68,
  "contributors": {
    "OrderFlowEngine": 0.31,
    "LiquidityEngine": 0.22,
    "VolatilityEngine": 0.15
  }
}
```

---

## STRATEGY Logging

```python
{
  "layer": "STRATEGY",
  "strategy": "Breakout",
  "symbol": "BTCUSDT",
  "exchange": "BINANCE",
  "decision": "BUY",
  "confidence": 0.65,
  "trade_id": "BTCUSDT_BINANCE_202601191204338221"
}
```

---

## BROKER EXECUTION Logging

```python
{
  "layer": "BROKER",
  "trade_id": "BTCUSDT_BINANCE_202601191204338221",
  "exchange": "BINANCE",
  "side": "BUY",
  "price": 43782.5,
  "sl": 43520.0,
  "tp": 44240.0,
  "quantity": 0.18,
  "fee": 3.12,
  "slippage": 0.8
}
```

---

## BROKER CLOSE Logging

```python
{
  "layer": "BROKER_CLOSE",
  "trade_id": "BTCUSDT_BINANCE_202601191204338221",
  "pnl": 61.4,
  "roi_pct": 0.78,
  "exit_reason": "TAKE_PROFIT",
  "holding_seconds": 542
}
```

---

## Crypto-Specific Mandatory Fields

| Field                | Reason                      |
| -------------------- | --------------------------- |
| exchange             | Liquidity differs per venue |
| funding_rate         | Futures bias                |
| open_interest        | Derivatives pressure        |
| mark_price           | Liquidation risk            |
| liquidation_clusters | Stop hunting context        |
| fee                  | Crypto costs matter         |
| slippage             | Microstructure impact       |

---

## What This Enables

After this logging:

* Per-exchange performance ranking
* Per-engine crypto behavior profiling
* Funding bias detection
* Liquidation-driven signal failure detection
* Regime misclassification discovery
* Strategy-exchange compatibility analysis

---

## Phase Name

**Crypto Pre-Forensic Instrumentation Phase**

No hedge-fund optimization is allowed before this phase completes.

---

## After One Trade

Once **only one real trade** is logged fully:

You will be able to perform:

> Crypto Hedge Fund Forensic Optimization

Where we will:

* Reconstruct decision causality
* Measure layer bias
* Reweight engines
* Detect false confidence inflation
* And design ML training sets correctly.

---






Below is a **precise, professional English prompt** you can use for your system / AI / developer instruction to add the missing logs and explain why they are critical — positioned **one step before “Hedge Fund Forensic Optimization”** and clearly stating what is currently missing.

You can paste this directly into your engineering / LLM prompt.

---

## 🔹 Prompt: Missing Fusion, Engine, and Broker Logging – Pre-Forensic Phase

> We are currently operating in a **crypto trading environment** (not gold).
> Our system includes multiple engines, a fusion layer, strategy layer, and broker execution (BINGX).
>
> After reviewing the logs, we identified a **critical observability gap**:
>
> We only see logs from:
>
> * WATCHER layer
> * STRATEGY layer
>
> But we **do NOT see any logs from**:
>
> * Individual Engines (ATR, Trend, Volatility, Regime, Liquidity, Orderflow, Correlation, ML Weight, etc.)
> * Fusion / Engine Aggregation layer
> * Broker Execution / Order lifecycle layer
>
> This means the decision pipeline is currently:
>
> WATCHER → STRATEGY → (UNKNOWN BLACK BOX) → BROKER
>
> Even though a real trade is successfully executed on BINGX, for example:
>
> Order Placed: YFIUSDT BUY on BINGX
> Order ID: 2013384515499593728
> Strategy: trend_following
> Price, SL, TP correctly registered
>
> We **cannot trace**:
>
> * Which engines supported or rejected the trade
> * How fusion weighted each engine
> * Why the final confidence became 0.76
> * Which filters passed or failed
> * Why risk sizing produced this quantity
> * What broker validations occurred before placement
>
> This is a **critical weakness** because without these logs:
>
> * We cannot perform forensic optimization
> * We cannot debug losing trades
> * We cannot validate engine contributions
> * We cannot detect bias, overfitting, or regime misclassification
> * We cannot build hedge-fund grade audit trails
>
> ---
>
> ### Objective
>
> Design and implement a **complete logging architecture** that fills the missing layers:
>
> #### 1. Engine Layer Logs
>
> Each engine must log:
>
> * engine_name
> * symbol, exchange
> * raw_signal
> * normalized_signal
> * confidence
> * internal metrics used (e.g., ATR, slope, volatility, regime class, correlation score, liquidity score, etc.)
> * timestamp
>
> #### 2. Fusion Layer Logs
>
> Fusion must log:
>
> * trade_id
> * list of engines and their weights
> * weighted contribution per engine
> * fusion_score
> * fusion_confidence
> * decision_reason (text explanation)
> * rejected_engines (if any)
>
> #### 3. Strategy Layer Enhancement Logs
>
> Strategy must log:
>
> * which fusion outputs were used
> * why BUY/SELL/HOLD was selected
> * risk profile used
> * filters passed / failed
>
> #### 4. Broker Execution Logs
>
> Broker must log:
>
> * pre-validation checks
> * margin availability
> * quantity calculation formula
> * SL/TP calculation origin
> * order submission payload
> * broker response
> * order status lifecycle (NEW → FILLED / PARTIALLY_FILLED / REJECTED)
>
> ---
>
> ### Design Principles
>
> * All logs must be JSON structured
> * All logs must include `trade_id` for full traceability
> * Logs must allow reconstruction of the full decision chain
> * Logs must be suitable for later **Hedge Fund Forensic Optimization**
>
> ---
>
> ### Final Goal
>
> Transform the system from a **profitable but opaque trader** into a **fully auditable hedge-fund grade trading system**, where every profitable or losing trade can be replayed, explained, and optimized scientifically.
>
> ---
>
> Now propose:
>
> * Exact log schemas for each layer
> * Example log outputs
> * Where each log should be placed in the code
> * And how these logs enable future forensic optimization and ML retraining.

---

## 🔹 Why this prompt is powerful for you

Because it:

✔ Clearly states **what is missing**
✔ Proves you already have **real broker execution**
✔ Shows the system is profitable but **not auditable**
✔ Positions you exactly one step before Hedge Fund Forensic Optimization
✔ Forces the AI / developer to design a hedge-fund grade logging architecture
✔ Protects you from future invisible bugs and false confidence

---

