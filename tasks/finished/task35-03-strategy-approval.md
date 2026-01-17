You are allowed—and encouraged—to **optimize, refactor, and correct** implemented strategies which is located in ./infrastructure/strategies as needed,
so they reach our required standard.
- no need to implement new strategies, just focus on make them readable!
---

### Read and Analyze Carefully

Before performing a full system analysis and achieving a **correct and comprehensive understanding**, **do not write any code**.

Our top priority is **correct system behavior first**.

---

> **If the Strategy is not yet healthy and reliable,
> a dynamic parameter system will only amplify noise.**

---

# 🧠 The Golden Rule of Hedge-Grade Architecture

> **Static correctness precedes dynamic optimization**

Meaning:

1️⃣ First, the logic must **work correctly**
2️⃣ Then it is allowed to **be optimized**
3️⃣ Only after that is it allowed to **adapt dynamically**

---

# 🥇 Correct Priority Order (Non-Negotiable)

## ✅ Phase 1 — Strategy & Watcher Hardening (Mandatory)

Without this phase:
* Hyperopt is meaningless
* Walk-Forward Optimization is misleading
* Canary deployment is dangerous

---

## ❌ What You Must NOT Do Yet

* Drift detection
* Automated retuning
* Live feedback loops

---

# 🧱 Phase 1 — What Exactly Needs to Be Done?

I’ll give this to you as **Instructions + Prompt**.

---

## 🎯 Phase 1 Objective

Finalize the implemented strategies under:
```
infrastructure/strategies
```

The real target is:

* They are **tradable**
* Their behavior is **explainable**
* They **work even without optimization**

---

## 🧩 Step-by-Step Instructions (Phase 1)

### 1️⃣ Freeze Market & Universe

Choose:

* 1 market regime (e.g. trending or ranging)
* 5–10 coin is enough
* Fixed timeframe (e.g. 5m)

📌 Goal:

> Remove noise to clearly understand behavior

---

### 2️⃣ Disable All Dynamic Systems (Temporarily)

Must be disabled:

* Hyperopt ❌
* Retune ❌
* Drift ❌
* Volatility scaling ❌

You need to simulate (Watcher → Engine → Fusion → ) for testing or use it if they are ready to use.
<Watcher → Engine → Fusion> → Strategy → Broker

---

### 4️⃣ Strategy Validation

Each strategy must, at minimum:

* Over 3–6 months:
* Produce at least **N trades** (e.g. 100)
* Trade in at least **3 different market conditions**

📌 If:

> A strategy does not trade without optimization
> → the strategy itself is flawed

---

### 5️⃣ Explainability Check (Critical)

After every backtest, you must be able to explain:

* Why it entered
* Why it exited
* Why it lost
* Why it won

If you cannot explain this:

> It is not ready

---

### 6️⃣ Stress Test Without Optimization

Perform the following:

* Increase SL by 20%
* Decrease TP by 20%
* Temporarily disable one watcher

📌 If the strategy collapses:

> It is over-engineered

---

### 7️⃣ Declare Strategy “Optimization-Eligible”

Only if **all** are true:

* Activity is sufficient
* Behavior is explainable
* Robust under stress

Then—and only then:

> It may enter Hyperopt

---

# 🧠 Final Summary (Very Important)

* ✔️ Yes — fixing Strategy is the **absolute first step**
* No need to implement new strategies, just focus on make them readable!
* ❌ Dynamic parameters before that are **dangerous**
* ✔️ When a strategy works without optimization
  → optimization finally becomes meaningful

---

## **Priority 0 — Data & Execution Sanity (Absolute Prerequisite)**

**Goal:** Ensure everything you see could actually happen.

* Clean data (no gaps, correct timestamps)
* Identical execution logic in backtest & live
* Fees, slippage, latency modeled

📌 Output:

> “Every trade I saw could realistically occur”

⛔ Without this, do nothing.

---

## **Priority 2 — Strategy Static Validation (No Optimization)**

**Goal:**
The strategy must breathe **on its own**.

* Disable hyperopt / retune / drift (Temporary)
* Minimum trade activity
* Explainability
* Stress tests

📌 Output:

> Strategy trades and is explainable

❌ If it only works with optimization → rewrite it

---

## **Priority 3 — Write a simple script (Strategy Readiness Gate) to make sure **

This is a **formal gate**, not an opinion.

Criteria:

* Minimum trades per window
* Works in ≥2 regimes
* Stable under stress

📌 Output:

> `[OPTIMIZATION-ELIGIBLE]`

Others:

* `[REJECTED]`
* `[NEEDS REVISION]`

---

## **Priority 4 — Hyperopt (Controlled, Not Greedy)**

**Goal:** Improve, not invent.

Rules:

* Narrow parameter ranges
* Activity constraints
* Risk-adjusted objective

📌 Output:

> A few sane candidates, not a monster

---

## **Priority 5 — Walk-Forward Optimization**

**Goal:** Time-stability validation.

* Sliding windows
* Reject unstable parameters
* Stability > Profit

📌 Output:

> Reliable seed parameters




## All Critical Rules Implemented

### **1. Architectural Compliance**

* [ ] Ensure full compatibility with the current Hexagonal Architecture.
* [ ] Verify that no part of the architecture (Watcher → Engine → Fusion → Strategy → Broker) is modified or broken.
* [ ] Confirm the strategies integrate without introducing tight coupling or side effects.

### **2. Integration & Functional Testing**
* [ ] Confirm there are no performance delays, lags, or misalignment issues.
* [ ] Check for indicator shifting errors or look-ahead problems.
* [ ] Ensure no survivorship bias or similar failure patterns appear.

### **3. Quality & Validation**
* [ ] Maintain Hexagonal Architecture integrity at all times.
* [ ] Prevent performance degradation or lag.
* [ ] Avoid look-ahead issues and misalignment.
* [ ] Validate all migrated features behave exactly as before.
* [ ] Ensure all code follows best practices and architectural rules.
* [ ] Keep the code DRY (no logic repetition).
* [ ] Verify that the project builds successfully.
* [ ] Ensure all automated tests pass.
* [ ] Perform a final full-system verification to guarantee 100% correctness.
* [ ] Perform some orders on bingx broker via using WFO_COINS coins to make sure all is functioning correctly and guarantee 100% correctness.
