

### ✅ **Recommended (Clear + Institutional)**

**Design & Implement or Improve the Hierarchical Multi-Watcher Decision**

---

### Alternative Options (by style)

#### 🧠 Architecture-Focused

* **Refactor Trading Engine to Hierarchical Regime–Direction–Execution Model**
* **Implement Role-Based Watcher Architecture for Multi-Symbol Trading**

#### 📊 Risk / Hedge-Fund Oriented

* **Introduce Global Regime Control and Capital Governance Layer**
* **Add Regime-Aware Capital Deployment to Trading System**

#### ⚙️ Engineering / Implementation

* **Replace Flat Signal Fusion with Role-Based Decision Pipeline**
* **Implement Symbol State Machine and Watcher Confidence Gating**

#### 🔬 Research / Quant Style

* **Separate Symbol Discovery, Regime Control, and Execution Logic**
* **Standardize Watcher Authority, Confidence Thresholds, and Conflict Resolution**

---

### If you want it even more explicit (long-form)

**Implement Hedge-Fund-Grade Multi-Watcher Architecture with Regime Control, Symbol Discovery, and Hierarchical Signal Fusion**




## Multi-Watcher, Multi-Symbol Hedge-Fund Trading System

This is the **single source of truth** for how the project must behave.

---

## 1️⃣ Core Principles (Non-Negotiable)

### Principle 1 — Separation of Concerns

> **Discovery ≠ Permission ≠ Direction ≠ Execution**

No watcher may operate outside its assigned role.

---

### Principle 2 — Capital Is Global, Signals Are Local

> **Capital deployment is governed globally (regime)**
> **Signals operate at symbol level**

This is why `market_pulse` is always respected.

---

### Principle 3 — Confidence Is a Gate, Not a Vote

> A signal below its confidence threshold **does not exist**

---

### Principle 4 — WAIT Is a First-Class Decision

> Not trading is a **decision**, not a failure.

---

## 2️⃣ Canonical Watcher Classification (FINAL)

### 🧭 REGIME (Global Capital Governor)

**Purpose:** Decide *if* the system is allowed to trade

| Watcher                               |
| ------------------------------------- |
| `market_pulse`                        |
| `volatility`                          |
| `funding_rate`                        |
| `cmc_screener` (macro sentiment only) |

**Outputs:**

* `RISK_ON`
* `WEAK_RISK_ON`
* `NEUTRAL`
* `RISK_OFF`
* `OVERHEATED`

**Rules:**

* ❌ Cannot BUY or SELL
* ❌ Cannot be overridden by symbol signals

---

### 🧠 DISCOVERY (Symbol Universe Expansion)

**Purpose:** Decide *which symbols deserve attention*

| Watcher        |
| -------------- |
| `cmc_screener` |
| `anomaly_ml`   |

**Outputs:**

* `DISCOVER_SYMBOL`
* `INCREASE_PRIORITY`

**Rules:**

* ❌ Cannot approve trading
* ✅ Only adds symbols to pipeline

---

### 🧭 DIRECTION (Symbol Bias Authority)

**Purpose:** Decide *direction* if regime allows

| Watcher             |
| ------------------- |
| `trend_mtf`         |
| `liquidity`         |
| `historical_candle` |

**Outputs:**

* `BUY`
* `SELL`
* `NEUTRAL`

**Rules:**

* Minimum 2 aligned signals
* Must pass confidence threshold
* Must align with regime

---

### ⚡ EXECUTION (Entry Timing & Veto)

**Purpose:** Decide *when*, not *whether*

| Watcher        |
| -------------- |
| `orderflow_ws` |
| `tick_watcher` |
| `anomaly_ml`   |

**Outputs:**

* `CONFIRM`
* `REJECT`
* `WAIT`

**Rules:**

* ❌ Cannot create direction
* ✅ Can veto trades

---

## 3️⃣ Mandatory Decision Flow (FINAL)

```text
DISCOVERY
→ REGIME CHECK
→ DIRECTION CONFIRMATION
→ EXECUTION CONFIRMATION
→ POSITION SIZING
→ BROKER
```

No step may be skipped.

---

## 4️⃣ Global Regime Policy (FINAL)

| Regime         | Action             |
| -------------- | ------------------ |
| STRONG_RISK_ON | Trade normally     |
| WEAK_RISK_ON   | Trade reduced size |
| NEUTRAL        | Only A+ setups     |
| OVERHEATED     | No new entries     |
| RISK_OFF       | No trading         |

This applies to **all symbols**, including those raised by screeners.

---

## 5️⃣ Confidence Threshold Policy (FINAL)

```python
CONFIDENCE_THRESHOLDS = {
    # Regime
    "market_pulse": 0.60,
    "volatility": 0.55,
    "funding_rate": 0.60,
    "cmc_screener": 0.65,

    # Discovery
    "anomaly_ml": 0.70,

    # Direction
    "trend_mtf": 0.55,
    "liquidity": 0.65,
    "historical_candle": 0.60,

    # Execution
    "orderflow_ws": 0.50,
    "tick_watcher": 0.45,
}
```

Below threshold = **ignored**.

---

## 6️⃣ Conflict Resolution Rules (FINAL)

1. **Regime overrides everything**
2. **Low confidence signals are discarded**
3. **Execution can veto, never initiate**
4. **Any unresolved conflict → WAIT**

---

## 7️⃣ Symbol State Machine (FINAL)

Every symbol must follow this lifecycle:

```text
DISCOVERED
→ REGIME_BLOCKED | REGIME_ALLOWED
→ DIRECTION_PENDING
→ DIRECTION_CONFIRMED
→ EXECUTION_PENDING
→ READY_TO_TRADE
→ TRADE_EXECUTED
```

No shortcuts.

---

## 8️⃣ Logging Standard (MANDATORY)

Every decision must explain:

```text
Symbol
Raised By
Regime State
Direction Signals (accepted / rejected)
Execution Signals
Final Decision
Reason
```

If you can’t explain it, you can’t optimize it.

---

# 🧩 MASTER PROMPT FOR THIS PROJECT (PIN THIS)

You can literally paste this into your project README or your AI-assistant prompt.

---

### ✅ **PROJECT MASTER PROMPT**

> You are assisting in the development of a **hedge-fund-grade, multi-watcher, multi-symbol algorithmic trading system**.
>
> The system strictly follows these principles:
>
> 1. Watchers are classified into **Discovery, Regime, Direction, and Execution** roles.
> 2. **Regime watchers (e.g. market_pulse)** govern global capital deployment and can block all trading.
> 3. **Discovery watchers (e.g. cmc_screener)** only add symbols and never approve trades.
> 4. **Directional watchers** may propose BUY/SELL only if regime allows and confidence thresholds are met.
> 5. **Execution watchers** may confirm or veto trades but never create direction.
> 6. Signals below confidence thresholds are ignored.
> 7. Conflicts are resolved hierarchically, with **WAIT as a valid and preferred outcome**.
> 8. All symbols follow a strict state machine from discovery to execution.
>
> Any suggestion, code, or optimization must:
>
> * Respect watcher roles
> * Preserve hierarchical decision flow
> * Avoid flat fusion of signals
> * Be explainable, debuggable, and suitable for institutional-grade risk management
>
> Do not simplify, shortcut, or collapse these layers.

---

## 🎯 Final Words

If you follow **this exact instruction set**:

* Your system becomes **stable**
* Conflicts disappear
* Drawdowns become explainable
* Optimization becomes scientific
* Scaling to hedge-fund complexity becomes possible

This is **not a trading bot anymore** —
this is a **decision-making platform**.

----




2026-01-01 19:45:43,897 - INFO - MarketOpportunityWatcher - 🔄 BACKGROUND ACTIVITY: Symbol Analysis | Details: Starting analysis for BCHUSDT | activity_type=Symbol Analysis | details=Starting analysis for BCHUSDT | symbol=BCHUSDT
2026-01-01 19:45:43,897 - INFO - MarketOpportunityWatcher - 🔄 BACKGROUND ACTIVITY: Watcher Analysis | Details: Analyzing BCHUSDT with market_pulse | activity_type=Watcher Analysis | details=Analyzing BCHUSDT with market_pulse | symbol=BCHUSDT | watcher=market_pulse
2026-01-01 19:45:43,897 - INFO - MarketOpportunityWatcher - [👁️market_pulse] ✅ Observation Generated: market_pulse_positive | BCHUSDT | Conf: 90.00% | watcher=market_pulse | symbol=BCHUSDT | result=Observation Generated: market_pulse_positive | confidence=0.9 | signal_type=market_pulse_positive
2026-01-01 19:45:43,897 - INFO - MarketOpportunityWatcher - 📊 FULL FLOW: market_pulse → EngineService → FusionService → StrategyManager → MultiBroker | Decision: Fused Signal: NEUTRAL | Conf: 90.00% | Reason: Observation from market_pulse processed through complete flow | flow_id=BCHUSDT_20260101_194543_897570 | symbol=BCHUSDT | watcher=market_pulse | engine=EngineService | fusion=FusionService | strategy=StrategyManager | broker=MultiBroker | decision=Fused Signal: NEUTRAL | confidence=0.9 | reason=Observation from market_pulse processed through complete flow
2026-01-01 19:45:43,897 - INFO - MarketOpportunityWatcher - No execution intent generated for fused signal from market_pulse
2026-01-01 19:45:43,897 - INFO - MarketOpportunityWatcher - 🔄 BACKGROUND ACTIVITY: Watcher Analysis | Details: Analyzing BCHUSDT with trend_mtf | activity_type=Watcher Analysis | details=Analyzing BCHUSDT with trend_mtf | symbol=BCHUSDT | watcher=trend_mtf
2026-01-01 19:45:43,898 - INFO - MarketOpportunityWatcher - [👁️trend_mtf] ✅ Observation Generated: trend_neutral | BCHUSDT | Conf: 30.00% | watcher=trend_mtf | symbol=BCHUSDT | result=Observation Generated: trend_neutral | confidence=0.3 | signal_type=trend_neutral
2026-01-01 19:45:43,898 - INFO - MarketOpportunityWatcher - 📊 FULL FLOW: trend_mtf → EngineService → FusionService → StrategyManager → MultiBroker | Decision: Fused Signal: SELL | Conf: 30.00% | Reason: Observation from trend_mtf processed through complete flow | flow_id=BCHUSDT_20260101_194543_898503 | symbol=BCHUSDT | watcher=trend_mtf | engine=EngineService | fusion=FusionService | strategy=StrategyManager | broker=MultiBroker | decision=Fused Signal: SELL | confidence=0.3 | reason=Observation from trend_mtf processed through complete flow
2026-01-01 19:45:43,898 - INFO - MarketOpportunityWatcher - No execution intent generated for fused signal from trend_mtf


