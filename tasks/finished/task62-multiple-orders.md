## Improved Problem Description

Despite `PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL = true`, the system is placing **multiple SELL orders for BTCUSDT**.
This indicates a **critical failure in the duplicate prevention mechanism**.

Log analysis (`./logs/*`) shows multiple entries like:

> `Telegram sent: Order Placed: BTCUSDT SELL`

This confirms that **multiple orders are being executed for the same symbol and direction**, which should not be possible when duplicate prevention is enabled.

The duplicate prevention logic is **not functioning as expected** and may be applied at the **wrong stage of the execution pipeline**.

---

## Observed Execution Flow

Current architecture:

```
Watcher → Engine → Fusion → Strategy → Broker
```

From the logs and behavior, it is evident that:

* Multiple execution intents for **BTCUSDT SELL** are generated
* These intents are processed (sometimes in parallel)
* Duplicate prevention is bypassed or ineffective

---

## Root Cause Analysis (Refined)

### What is happening

1. **Multiple execution intents** for the same symbol and direction are generated at the **strategy layer**
2. These intents are placed into `AutoDetectionOrchestrator.opportunity_queue`
3. The queue processes them sequentially
4. **Duplicate prevention happens only at execution time**
5. By that time, the intents already exist as separate entities

As a result, the system **correctly processes multiple distinct intents**, even though they represent the *same trade idea*.

---

### Why duplicate prevention fails

The duplicate prevention mechanism is applied **too late in the pipeline**.

Instead of preventing *intent creation*, it attempts to prevent *order execution*, which is already too late once multiple intents exist.

---

## Possible Technical Issues Identified

### 1. Incorrect prevention level

* Duplicate checks occur in the **Execution Service**
* They should occur **before or during intent creation**

### 2. Parallel intent generation

* Multiple watchers or strategies may emit signals simultaneously
* This results in multiple intents for the same symbol/direction

### 3. Thread safety concerns

* Shared state used for tracking open or pending orders may not be thread-safe
* Check-and-add logic may not be atomic

### 4. Service overlap

* `BrokerExecutionService` and `MultiBrokerExecutionService` may both execute paths that bypass the same duplicate check

---

## Why Only BTC Orders Were Successfully Placed (New Investigation)

Although the watcher discovered **many symbols**, only **BTC orders were successfully placed**.
This strongly suggests **symbol-specific gating or filtering** later in the pipeline.

### Likely reasons:

#### 1. Strategy conditions only satisfied for BTC

* Other symbols may fail strategy filters (volume, volatility, indicators, confidence score)
* Logs may show intents created but rejected before execution

#### 2. Broker or exchange constraints

* BTC may be the only symbol:

  * Enabled for trading
  * Passing minimum order size
  * Passing margin / balance checks

#### 3. Risk management rules

* Max concurrent trades per symbol or per account
* BTC may consume available risk budget, blocking others

#### 4. Silent rejection of other symbols

* Other symbols may generate intents but fail:

  * Validation
  * Precision rules
  * Market status checks
* These failures may not be logged clearly

#### 5. Duplicate prevention working only per symbol

* Duplicate prevention may **block other symbols incorrectly**
* Or BTC bypasses the block due to timing or race conditions

---

## Required Criteria (Acceptance / Investigation Criteria)

### Functional Criteria

1. **No duplicate execution intents**

   * Only one execution intent per `(symbol, direction)` within a defined time window

2. **Early duplicate prevention**

   * Deduplication must occur:

     * At the **strategy layer**, or
     * Inside the **AutoDetectionOrchestrator queue**

3. **Atomic checks**

   * Check-and-register logic must be atomic and thread-safe

4. **Clear rejection logging**

   * Every rejected intent must log:

     * Symbol
     * Direction
     * Reason for rejection

---

### Observability Criteria

5. **Intent lifecycle visibility**

   * Logs must show:

     * Signal received
     * Intent created
     * Intent queued
     * Intent executed or rejected

6. **Per-symbol diagnostics**

   * Ability to trace why a symbol was discovered but not traded

---

### Architectural Criteria

7. **Single source of truth**

   * One centralized component responsible for:

     * Intent deduplication
     * Trade direction locking per symbol

8. **No execution-layer deduplication**

   * Execution services should assume intents are already valid and unique

---

## Recommended Fix (Summary)

* Move duplicate prevention **upstream**
* Deduplicate **before execution intents are created**
* Alternatively, deduplicate inside `AutoDetectionOrchestrator` before enqueueing
* Enforce `(symbol + direction + time window)` uniqueness
* Improve logging for symbol rejection paths




--------------------------------
--------------------------------
--------------------------------
--------------------------------

Duplicate Trade Prevention Not Working – Multiple BTC SELL Orders Despite `PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL=true`

---

### **Issue Type**

Bug / Critical Defect

---

### **Priority**

🚨 High / Blocker

---

### **Environment**

* Trading Engine (Auto Detection)
* Execution Services
* Production / Staging (verify)

---

### **Description**

Despite `PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL = true`, the system places **multiple SELL orders for BTCUSDT**.

Log analysis (`./logs/*`) shows repeated messages:

> `Telegram sent: Order Placed: BTCUSDT SELL`

This confirms that **duplicate trades for the same symbol and direction are being executed**, which should be impossible when duplicate prevention is enabled.

This is a **critical failure** in the duplicate prevention mechanism and can lead to:

* Overexposure
* Risk limit violations
* Unexpected financial losses

---

### **Current Execution Flow**

```
Watcher → Engine → Fusion → Strategy → Broker
```

---

### **Observed Behavior**

* Multiple execution intents are generated for **BTCUSDT SELL**
* These intents are queued in `AutoDetectionOrchestrator.opportunity_queue`
* The queue processes intents sequentially
* Duplicate prevention occurs only at execution time
* By execution time, multiple intents already exist

---

### **Expected Behavior**

* Only **one execution intent per (symbol, direction)** should exist within a defined time window
* Duplicate execution intents must be **prevented before order execution**
* No duplicate orders should reach the broker layer

---

### **Root Cause Analysis**

Duplicate prevention is applied **too late in the pipeline**.

1. The **strategy layer generates multiple execution intents** for the same symbol and direction
2. These intents are queued in `AutoDetectionOrchestrator.opportunity_queue`
3. Duplicate prevention happens in the execution service
4. Execution service processes already-separated intents, allowing duplicates

Additionally, potential contributing factors:

* Parallel signal generation (multiple watchers / strategies)
* Thread-safety issues in shared trackers
* Non-atomic check-and-add logic
* Overlapping execution paths between `BrokerExecutionService` and `MultiBrokerExecutionService`

---

### **Additional Finding**

**Only BTC orders were successfully placed**, despite many symbols being discovered by the watcher.

Possible causes:

* Strategy conditions satisfied only for BTC
* Broker / exchange constraints for other symbols
* Risk management blocking non-BTC trades
* Silent validation failures for other symbols
* Symbol-specific timing or race conditions

This requires further investigation and clearer logging.

---

### **Acceptance Criteria**

#### Functional

* [ ] Only **one execution intent per (symbol, direction)** can be created within a configurable time window
* [ ] Duplicate prevention occurs **before execution intent creation** or **during orchestrator queueing**
* [ ] No duplicate orders reach the broker layer

#### Concurrency & Safety

* [ ] Deduplication logic is **thread-safe**
* [ ] Check-and-register logic is **atomic**

#### Observability

* [ ] Logs clearly show:

  * Signal received
  * Intent created
  * Intent queued
  * Intent executed or rejected
* [ ] Rejected intents include:

  * Symbol
  * Direction
  * Reason for rejection

#### Architecture

* [ ] Single centralized component is responsible for intent deduplication
* [ ] Execution services assume intents are already unique and valid

---

### **Proposed Fix / Next Steps**

* Move duplicate prevention **upstream**:

  * Strategy layer **OR**
  * `AutoDetectionOrchestrator` (before enqueue)
* Enforce uniqueness using:

  * `(symbol + direction + time window)`
* Improve rejection logging for non-executed symbols
* Review execution service overlap (`BrokerExecutionService` vs `MultiBrokerExecutionService`)

---

### **Impact / Risk**

* Financial risk due to duplicate trades
* Strategy behavior deviates from configuration
* Loss of trust in automation safeguards

---

### **Attachments**

* Relevant log excerpts (`./logs/*`)
* Telegram notification screenshots (if available)


