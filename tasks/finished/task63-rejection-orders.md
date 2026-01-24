I recently identified a critical issue in production mode.

Some BTC/USDT orders are being placed immediately at startup without correctly passing through the full hedge-fund execution pipeline. This violates the intended system design.

Looking at the logs (./logs/*), I can see that the system is successfully placing orders for BTCUSDT SELL (short
positions). The real issue is that other symbols are not generating execution intents. This could be because:


### Intended Execution Flow . Canonical Hedge Fund Decision Flow

The correct flow must always be:

```
Watcher → Engine → Fusion → Strategy → Broker
```

### Symbol Discovery

Symbols are discovered by the **Watcher** during the **initiation step**, but discovery must never trigger an order directly. All discovered symbols must pass through:

1. Engine validation
2. Fusion aggregation logic
3. Strategy evaluation
4. Risk management checks
5. Only then → Broker execution

### Current Problems

1. **Order Bypass Issue**
   BTC/USDT orders are sometimes placed directly without completing the full flow, especially bypassing Strategy and Risk validation.

2. **Shutdown Execution Issue**
   Even after stopping the system, some BTC orders are still executed. This suggests that:

   * Orders remain queued
   * The execution queue continues processing after shutdown
   * Or broker calls are not properly locked during stop events

### Required Fixes

Please review and correct:

* Watcher symbol discovery handling
* Engine routing logic
* Fusion decision gating
* Strategy validation enforcement
* Broker execution lock mechanism
* Risk management enforcement

### Mandatory Rules

The system must guarantee that:

* No order can bypass Strategy evaluation.
* No order can be sent to the Broker after system stop.
* All execution queues are flushed, cancelled, or locked on shutdown.
* Watcher discovery only triggers evaluation — never execution.

### Deliverables

Please provide:

* The corrected code implementation
* A clear report explaining:
  * What caused the issue
  * How it was fixed
  * How future bypasses are prevented

I have attached the responsibility definition of each flow to clarify the intended architecture.




---
## 6️⃣ Layer-by-Layer Audit Prompts (Reusable)

Use these prompts to **verify correct implementation**.

---

### 🔍 Prompt 1 — Watcher Audit

```
Verify that the Watcher layer:
- Produces only market observations or raw signals
- Does NOT assign BUY or SELL
- Does NOT select or reference any strategy
- Does NOT define SL/TP
- Does NOT create or submit orders

If any of the above are violated, flag an architecture breach.
```

---

### 🔍 Prompt 2 — Engine Audit

```
Verify that the Engine:
- Interprets raw signals
- Assigns strength and confidence only
- Does NOT trigger execution
- Does NOT select strategy
```

---

### 🔍 Prompt 3 — Fusion Audit

```
Verify that Fusion:
- Aggregates interpreted signals
- Produces dominance or HOLD states
- HOLD is contextual and reversible
- Contains no strategy or capital logic
```

---

### 🔍 Prompt 4 — Strategy Audit (Critical)

```
Verify that Strategy:
- Is the ONLY layer selecting strategies
- Accepts or rejects fused signals
- Calls Risk Management
- Produces execution intent only after approval
```

---

### 🔍 Prompt 5 — Broker Audit

```
Verify that Broker:
- Receives fully-formed orders
- Rejects orders without SL and TP
- Does NOT modify intent or strategy
```


---
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
---

* [ ] Ensure full compatibility with the current Hexagonal Architecture.
* [ ] Verify that no part of the architecture (Watcher → Engine → Fusion → Strategy → Broker) is modified or broken.
* [ ] Confirm the strategies integrate without introducing tight coupling or side effects.
* [ ] Confirm and place orders on bingx, so that we have SUCCESSFUL ORDERS PLACED ON BINGX VST BROKER.

### **2. Integration & Functional Testing**
* [ ] Confirm there are no performance delays, lags, or misalignment issues.
* [ ] Check for indicator shifting errors or look-ahead problems.
* [ ] Ensure no survivorship bias or similar failure patterns appear.

### **3. Quality & Validation**
* [ ] Maintain Hexagonal Architecture integrity at all times.
* [ ] Better architecture: Each component now has a single responsibility. SOLID principals must be followed for coding!
* [ ] Prevent performance degradation or lag.
* [ ] Avoid look-ahead issues and misalignment.
* [ ] Validate all migrated features behave exactly as before.
* [ ] Ensure all code follows best practices and architectural rules.
* [ ] Keep the code DRY (no logic repetition).
* [ ] Verify that the project builds successfully.
* [ ] Ensure all automated tests pass.
* [ ] Perform a final full-system verification to guarantee 100% correctness.
* [ ] The system must be fully functional and able to order placement via mentioned flow (Watcher → Engine → Fusion → Strategy → Broker)


