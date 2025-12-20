# 🎯 FINAL EXECUTION TASK

## **Watcher Perfection Task (Phase 1 – Watcher-Only Scope)**

### Scope Boundary (Hard Limit)

✅ You are allowed to:

* Modify watcher **logic**
* Refine watcher **signals**
* Improve watcher **noise control**
* Improve watcher **explainability**
* Improve watcher **robustness**
* Improve watcher **configuration & defaults**

❌ You are NOT allowed to:

* Touch strategies
* Touch engines
* Add dynamic parameters
* Add optimization logic
* Add feedback loops
* Change architecture flow

---

## 🧠 Primary Objective

Transform all existing watchers into **hedge-grade market sensors** that:

* Emit **meaningful**, **stable**, and **explainable** signals
* Are **enabled by default**, but **fully controllable via config**
* Can safely feed Engines without poisoning downstream logic
* Remain useful **without any optimization or tuning**

---

## 🧱 Global Rules (Apply to ALL Watchers)

These rules are **non-negotiable** and must be enforced uniformly.

### Rule 1 — Default Enablement

* Every watcher must start with `enabled = true`
* Each watcher must support `enabled = false` via `.env`
* Disabled watcher:

  * Emits NOTHING
  * Leaves NO side effects
  * Allocates NO unnecessary resources

---

### Rule 2 — Pure Sensor Contract

A watcher MUST:

* Observe market state
* Detect a condition
* Emit a signal

A watcher MUST NOT:

* Decide trades
* Encode strategy logic
* Implicitly bias direction
* Depend on other watchers

---

### Rule 3 — Deterministic Behavior

Given the same historical input:

* The watcher must emit the **same signals**
* No randomness
* No hidden state drift
* No time-dependent side effects

---

## 🧩 Watcher-by-Watcher Improvement Tasks

Below is the **exact improvement focus** for EACH watcher type you listed.

---

### 1️⃣ MarketPulseWatcher

**Primary Risk:**
Overlapping signals with Trend / Momentum engines → hidden strategy logic

**Mandatory Improvements:**

* Separate **momentum**, **trend**, and **volume** into clearly explainable sub-scores
* Ensure final signal score is:

  * monotonic
  * bounded
  * explainable in plain English
* Add explicit **“NO SIGNAL” zone** to avoid constant firing

**Validation Criteria:**

* Does NOT trigger on minor price noise
* Trigger frequency is stable across symbols
* Can explain every trigger as:

  > “Momentum + volume expansion exceeded baseline”

---

### 2️⃣ VolatilityWatcher

**Primary Risk:**
Always firing during high-vol regimes → unusable noise

**Mandatory Improvements:**

* Explicitly distinguish:

  * volatility expansion
  * volatility compression
* Separate:

  * detection of regime
  * emission of actionable signal
* Prevent firing during already-expanded volatility unless transition is detected

**Validation Criteria:**

* Rare during flat volatility
* Fires mainly on **regime change**
* Does NOT depend on TP/SL assumptions

---

### 3️⃣ TrendMTFWatcher

**Primary Risk:**
Implicit strategy bias via multi-timeframe weighting

**Mandatory Improvements:**

* Each timeframe must emit an **independent trend state**
* Alignment must be explicit, not weighted magic
* Divergence must be detectable and emitted as metadata

**Validation Criteria:**

* Can explain:

  > “Short-term up, long-term flat → partial alignment”
* No hidden averaging logic
* Clear alignment states: ALIGNED / MIXED / CONFLICTED

---

### 4️⃣ AnomalyMLWatcher

**Primary Risk (Very Serious):**
False authority due to ML opacity

**Mandatory Improvements:**

* Enforce strict bounds on anomaly score
* Emit **confidence + anomaly type**
* Add hard suppression rules to avoid frequent triggers

**Absolute Requirement:**
If anomaly cannot be explained as:

> “This deviates from recent distribution by X sigma”

→ REJECT or simplify the model

**Validation Criteria:**

* Extremely low trigger frequency
* Triggers are visually obvious in price
* No “black box” outputs allowed

---

### 5️⃣ OrderFlowWSWatcher

**Primary Risk:**
Microstructure noise & overfitting to order book flicker

**Mandatory Improvements:**

* Add temporal confirmation (not single snapshot)
* Separate:

  * imbalance detection
  * persistence validation
* Explicit cooldown after trigger

**Validation Criteria:**

* Does NOT trigger on transient spoofing
* Triggers correlate with actual short-term movement
* Can explain:

  > “Sustained bid imbalance over N windows”

---

### 6️⃣ CMCScreener

**Primary Risk:**
Not a watcher, but a universe selector → scope creep

**Mandatory Improvements:**

* Reclassify output as:

  * universe signal
  * NOT trade signal
* Enforce very low update frequency
* Must NEVER emit BUY/SELL directly

**Validation Criteria:**

* Pure filtering role
* Deterministic outputs
* No intraday noise sensitivity

---

### 7️⃣ FundingRateWatcher

**Primary Risk:**
Always-on bias during extreme funding

**Mandatory Improvements:**

* Detect **change**, not level
* Separate:

  * extreme funding
  * funding acceleration
* Enforce long cooldown windows

**Validation Criteria:**

* Rare signals
* Mostly contrarian relevance
* Clear explanation:

  > “Funding extreme + acceleration reversal”

---

### 8️⃣ LiquidityWatcher

**Primary Risk:**
Subjective interpretation of “liquidity zones”

**Mandatory Improvements:**

* Liquidity levels must be:

  * derived
  * reproducible
  * timestamped
* Separate:

  * liquidity identification
  * liquidity sweep detection

**Validation Criteria:**

* Levels persist across candles
* Sweeps align with volatility spikes
* No repainting allowed

---

### 9️⃣ HistoricalCandleWatcher

**Primary Risk:**
Pattern overfitting & hindsight bias

**Mandatory Improvements:**

* Limit to a **small, justified** set of patterns
* Enforce strict confirmation rules
* No single-candle signals allowed

**Validation Criteria:**

* Patterns are rare
* Patterns are explainable visually
* No look-ahead contamination

---

## 📄 Required Deliverable (Watcher-Only)

Produce a **Watcher Perfection Report** with:

For EACH watcher:

* Purpose (1 sentence)
* What market condition it detects
* Expected trigger frequency
* Known failure modes
* Noise suppression mechanisms
* `[REJECTED] / [NEEDS REVISION] / [WATCHER-READY]`

---

## 🚨 Automatic Rejection Conditions

A watcher MUST be rejected if:

* It fires constantly
* It only works with tuning
* It embeds strategy logic
* It cannot be explained in plain language
* It violates Hexagonal Architecture boundaries

---

## ✅ Phase 1 Exit Gate (Watcher Complete)

You may exit this phase ONLY if:

* All watchers are watcher-ready or explicitly rejected
* All are enabled by default and config-disable verified
* No watcher depends on optimization
* No watcher leaks strategy intent

Only after this:

> Engines may be validated
> Strategies may breathe
> Optimization may eventually exist

---

## 🧠 Final Truth (Do Not Forget)

> **Bad watchers create good-looking but fake strategies.**
> **Perfect watchers make even simple strategies powerful.**



---
We need to test the system’s performance with respect to each watcher. So:

* Disable all watchers.
* Then enable them one by one.
* For each watcher, give me a report on:

  * Which coins were triggered/processed
  * Why certain coins were rejected
* For each watcher, tell me:

  * Its strengths
  * Its weaknesses
* Give me recommendations on how to improve it, if improvement is needed.
