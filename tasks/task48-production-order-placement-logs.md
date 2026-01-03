Below is a **clean, refactored, hedge-fund–grade “advanced audit prompt”** you can reuse verbatim with any senior quant, AI agent, or internal reviewer to **re-check your Risk Management & Execution flow**.
I’ve also included **explicit requirement breakdowns**, **diagnostic focus**, and **advanced suggestions**, without asking for re-implementation (audit + fixes only).

---

## 1️⃣ Refactored Core Requirement (Executive Version)

> **Objective**
> Perform a **full post-implementation audit** of an already-implemented multi-engine trading system to identify **why signals fail to transition correctly and why SL/TP are missing during live order placement**, while ensuring institutional-grade risk management compliance.

> **Critical Constraint**
> ⚠️ **Do NOT re-implement the system**.
> Only **inspect, verify, diagnose, and surgically fix broken logic paths** based on logs, watchers, fusion, strategy, and broker layers.
> Maintain Hexagonal Architecture integrity at all times.
> Better architecture: Each component now has a single responsibility. SOLID principals must be followed for coding!
> Prevent performance degradation or lag.
> Avoid look-ahead issues and misalignment.
> Validate all migrated features behave exactly as before.
> Ensure all code follows best practices and architectural rules.
> Keep the code DRY (no logic repetition).
> Verify that the project builds successfully.
> Ensure all automated tests pass.
> Perform a final full-system verification to guarantee 100% correctness.
> The system must be fully functional and able to order placement via mentioned flow (Watcher → Engine → Fusion → Strategy → Broker)

---

### 🔍 **Advanced Trading System Audit & Risk Review Prompt**

You are acting as a **Senior Quant Systems Auditor & Execution Engineer** for a hedge-fund-grade trading system.

The system is already running in production mode via:

```bash
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
```

Your task is **NOT to rebuild**, but to **audit, validate, and fix broken execution logic**.

---

### 🧠 **Scope of Analysis (Mandatory)**

Carefully analyze:

* `./logs` (production logs only)
* Watcher outputs
* SignalProcessor decisions
* Fusion weighting logic
* Strategy constraints
* Risk Management integration
* Broker execution adapters

---

### 🔄 **Execution Flow That MUST Be Respected**

Ensure the **true trading flow** is honored end-to-end:

```
Watcher → Engine → Fusion → Strategy → Broker
```

* Signals must **evolve**, not terminate
* HOLD must be **contextual**, not terminal
* Fusion must allow **actionable dominance**
* Strategy must **finalize execution-ready orders**
* Broker must receive **fully risk-wrapped orders**

---

### 🚨 **Primary Failures to Investigate**

#### 1️⃣ HOLD → BUY/SELL Transition Failure

Identify **exactly why signals fail to transition**:

* Threshold logic errors
* Score normalization mistakes
* Fusion weighting dilution
* Regime or volatility filters blocking execution
* Confidence caps or safety guards
* Structural HOLD bias due to conservative defaults

📌 Pay special attention to:

```
infrastructure/watchers/adapters/*.py
```

---

#### 2️⃣ SL/TP Missing During Order Placement (CRITICAL)

Orders are being placed **without SL/TP**, which is **institutionally unacceptable**.

You must:

* Trace **where SL/TP is dropped**
* Verify whether:

  * Risk Manager calculates SL/TP but doesn’t attach it
  * Strategy layer ignores risk outputs
  * Broker adapter silently discards SL/TP
* Fix the logic so **NO order can reach Broker without SL/TP**

⚠️ Market orders **must still carry stop-loss & take-profit definitions**, either:

* As bracket orders
* Or via immediate contingent orders

---

#### 3️⃣ Dynamic Risk Management Validation

Ensure the system supports and enforces:

* Dynamic SL/TP based on:

  * ATR / volatility regime
  * Market structure
  * Confidence score
* Risk-adjusted position sizing
* Max loss per trade enforcement
* Max portfolio heat enforcement
* Symbol-specific constraints (min lot, tick size, contract validity)

---

#### 4️⃣ Broker Execution Guardrails

From the logs provided, orders fail due to:

* Invalid or paused symbols
* Broker-specific contract mismatches

You must verify:

* Symbol normalization layer
* Broker contract whitelist enforcement **before execution**
* Pre-trade validation to prevent rejected orders
* Proper error bubbling without killing signal flow

---

### 🧾 **Provided Production Failures (Use These Logs)**

You must explicitly reference and reason from these failures:

* Orders executed without SL/TP
* Broker rejecting symbols:

  * `ICX-USDT is paused`
  * `WBETH-USDT not exist`
* Strategy still sending execution commands despite invalid contracts

---

### 🛠 **Expected Outcomes**

You must deliver:

1. **Root-cause explanation** for:

   * HOLD bias
   * Missing SL/TP
   * Invalid symbol execution
2. **Exact logic points where fixes are required**
3. **Risk-management enforcement guarantees**
4. **Confirmation that final execution is strategy-approved**
5. **No re-implementation**, only targeted fixes

---

### 🧠 **Institutional Standard Requirement**

No trade may ever be executed unless:

* SL and TP are explicitly defined
* Risk Manager has approved the trade
* Strategy has finalized the order
* Broker symbol is validated
* Execution failure does NOT break the signal pipeline

---

## 3️⃣ Explicit Risk Management Requirements (Checklist)

Use this as a validation checklist.

### ✅ Mandatory Before Broker Execution

> SL defined
> TP defined
> Risk per trade < configured max
> Risk-adjusted quantity computed
> Symbol validated for broker
> Strategy explicitly approves execution

### ❌ Never Allowed

* Market order without SL/TP
* Execution from watcher layer
* Broker-specific logic leaking into strategy
* Silent dropping of risk parameters
* HOLD used as a terminal state

---

## 4️⃣ Advanced Suggestions (Non-Implementation)

These are **architectural validations**, not rewrites:

### 🔹 1. “Execution Readiness Gate”

Introduce a **final validation gate** before broker dispatch:

```
if not order.has_sl_tp():
    reject_execution()
```

---

### 🔹 2. Risk Ownership Rule

Only **Risk Manager** may define:

* SL
* TP
* Max exposure
* Position sizing

Strategy may **accept or reject**, never override.

---

### 🔹 3. Symbol Pre-Validation Cache

Cache valid broker contracts at startup and **block invalid symbols upstream**, not at broker adapter level.

---

### 🔹 4. HOLD as a Dynamic State

HOLD should:

* Decay over time
* Be overridden by strong fusion dominance
* Never permanently suppress execution

---

## 5️⃣ Final Reminder

* 🚫 No re-implementation
* 🔍 Diagnose → Fix → Validate
* 🧠 Institutional-grade execution discipline
* ⚠️ SL/TP enforcement is non-negotiable

---

The issues on log in production mode! 
```
2025-12-30 23:37:19,052 ℹ️INFO MarketOpportunityWatcher - 🎯 EXECUTING TRADE: SELL for ICXUSDT with confidence 89.94%
2025-12-30 23:37:19,122 ℹ️INFO BrokerExecutionService - 🎯 EXECUTING ORDER ON MultiBroker: Order(symbol='ICXUSDT', side=<OrderSide.SELL: 'SELL'>, quantity=3331.2673379711773, price=Money(amount=Decimal('0.054'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2025, 12, 30, 23, 37, 19, 122556), parent_signal=None, risk_adjusted_quantity=None)
2025-12-30 23:37:19,122 ℹ️INFO MultiBrokerExecutionService - 🎯 BINGX ORDER PLACEMENT ENABLED - EXECUTING ORDER ON BINGX: Order(symbol='ICXUSDT', side=<OrderSide.SELL: 'SELL'>, quantity=3331.2673379711773, price=Money(amount=Decimal('0.054'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2025, 12, 30, 23, 37, 19, 122556), parent_signal=None, risk_adjusted_quantity=None)
2025-12-30 23:37:19,123 ℹ️INFO MultiBrokerExecutionService - 🎯 EXECUTING ORDER ON BINGX: Order(symbol='ICXUSDT', side=<OrderSide.SELL: 'SELL'>, quantity=3331.2673379711773, price=Money(amount=Decimal('0.054'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2025, 12, 30, 23, 37, 19, 122556), parent_signal=None, risk_adjusted_quantity=None)
2025-12-30 23:37:19,330 ❌ERROR MultiBrokerExecutionService - ❌ FAILED TO EXECUTE ORDER ON BINGX: Failed to place order: ICX-USDT is pause currently,all validted symbols in api:/openApi/swap/v2/quote/contracts, please verify it
2025-12-30 23:37:19,330 ❌ERROR BrokerExecutionService - ❌ FAILED TO EXECUTE ORDER ON MultiBroker: Failed to place order: ICX-USDT is pause currently,all validted symbols in api:/openApi/swap/v2/quote/contracts, please verify it
2025-12-30 23:37:19,330 ❌ERROR MarketOpportunityWatcher - Error executing trade for signal: Failed to place order: ICX-USDT is pause currently,all validted symbols in api:/openApi/swap/v2/quote/contracts, please verify it
2025-12-30 23:37:19,337 ❌ERROR MarketOpportunityWatcher - Traceback: Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/watchers/market_opportunity_watcher.py", line 1659, in _execute_signal_trade
    execution_id = self.execution_service.execute_order(order)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/services/broker_execution_service.py", line 155, in execute_order
    order_id = self.broker.execute_order(order)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/multi_broker_service.py", line 229, in execute_order
    order_id = broker.place_order(order)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/adapters/bingx_adapter.py", line 98, in place_order
    raise Exception(f"Failed to place order: {result['error']}")
Exception: Failed to place order: ICX-USDT is pause currently,all validted symbols in api:/openApi/swap/v2/quote/contracts, please verify it

2025-12-30 23:37:19,337 ℹ️INFO MarketOpportunityWatcher -   ⚡ BROKER: ❌ Failed | Order execution failed: Failed to place order: ICX-USDT is pause currently,all validted symbols in api:/openApi/swap/v2/quote/contracts, please verify it | Conf: 89.94% | symbol=ICXUSDT | stage=broker | status=Failed | details=Order execution failed: Failed to place order: ICX-USDT is pause currently,all validted symbols in api:/openApi/swap/v2/quote/contracts, please verify it | confidence=0.8994421812522179


2025-12-30 23:37:25,668 ℹ️INFO MultiBrokerExecutionService - 🎯 BINGX ORDER PLACEMENT ENABLED - EXECUTING ORDER ON BINGX: Order(symbol='WBETHUSDT', side=<OrderSide.SELL: 'SELL'>, quantity=0.037276537291509426, price=Money(amount=Decimal('3182.03'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2025, 12, 30, 23, 37, 25, 668205), parent_signal=None, risk_adjusted_quantity=None)
2025-12-30 23:37:25,668 ℹ️INFO MultiBrokerExecutionService - 🎯 EXECUTING ORDER ON BINGX: Order(symbol='WBETHUSDT', side=<OrderSide.SELL: 'SELL'>, quantity=0.037276537291509426, price=Money(amount=Decimal('3182.03'), currency='USDT'), order_type='MARKET', position_side='SHORT', stop_price=None, time_in_force='GTC', client_order_id=None, strategy_name='balanced_strategy', timestamp=datetime.datetime(2025, 12, 30, 23, 37, 25, 668205), parent_signal=None, risk_adjusted_quantity=None)
2025-12-30 23:37:25,876 ❌ERROR MultiBrokerExecutionService - ❌ FAILED TO EXECUTE ORDER ON BINGX: Failed to place order: WBETH-USDT not exist, please verify it in api: /openApi/swap/v2/quote/contracts
2025-12-30 23:37:25,876 ❌ERROR BrokerExecutionService - ❌ FAILED TO EXECUTE ORDER ON MultiBroker: Failed to place order: WBETH-USDT not exist, please verify it in api: /openApi/swap/v2/quote/contracts
2025-12-30 23:37:25,876 ❌ERROR MarketOpportunityWatcher - Error executing trade for signal: Failed to place order: WBETH-USDT not exist, please verify it in api: /openApi/swap/v2/quote/contracts
2025-12-30 23:37:25,877 ❌ERROR MarketOpportunityWatcher - Traceback: Traceback (most recent call last):
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/watchers/market_opportunity_watcher.py", line 1659, in _execute_signal_trade
    execution_id = self.execution_service.execute_order(order)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/services/broker_execution_service.py", line 155, in execute_order
    order_id = self.broker.execute_order(order)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/multi_broker_service.py", line 229, in execute_order
    order_id = broker.place_order(order)
  File "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/adapters/bingx_adapter.py", line 98, in place_order
    raise Exception(f"Failed to place order: {result['error']}")
Exception: Failed to place order: WBETH-USDT not exist, please verify it in api: /openApi/swap/v2/quote/contracts

2025-12-30 23:37:25,877 ℹ️INFO MarketOpportunityWatcher -   ⚡ BROKER: ❌ Failed | Order execution failed: Failed to place order: WBETH-USDT not exist, please verify it in api: /openApi/swap/v2/quote/contracts | Conf: 59.31% | symbol=WBETHUSDT | stage=broker | status=Failed | details=Order execution failed: Failed to place order: WBETH-USDT not exist, please verify it in api: /openApi/swap/v2/quote/contracts | confidence=0.5930752997885087
```