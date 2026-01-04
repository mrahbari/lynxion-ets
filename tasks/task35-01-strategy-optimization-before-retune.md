In the future, I plan to make the parameters dynamic.
We will review that in detail in a separate test later.

For now, the priority is to **prepare the system correctly for the future**.
So we will focus on the points below until our strategies are finalized.

You are allowed—and encouraged—to **optimize, refactor, and correct** strategies as needed so they reach our required standard.

---

### Read and Analyze Carefully

Before performing a full system analysis and achieving a **correct and comprehensive understanding**, **do not write any code**.

Our top priority is **correct system behavior first**.

---

> **If the Strategy / Watcher is not yet healthy and reliable,
> a dynamic parameter system will only amplify noise.**

---

# 🧠 The Golden Rule of Hedge-Grade Architecture

> **Static correctness precedes dynamic optimization**

Meaning:

1️⃣ First, the logic must **work correctly**
2️⃣ Then it is allowed to **be optimized**
3️⃣ Only after that is it allowed to **adapt dynamically**

Right now, you are exactly **between Phase 1 and Phase 2**.

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
* 5–10 coins are enough
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

Only keep:

> Strategy + Watcher + Execution

---

### 3️⃣ Watcher Validation (Watcher First, Then Strategy)

For each watcher, answer:

* Does it trigger on historical data?
* How many times per month?
* Is it correlated with price movement?
* Is it noisy?

Rules:

* Watcher that never triggers → must be fixed until it does
* Watcher that triggers constantly → over-noisy, must be refined

---

### 4️⃣ Strategy Activity Validation

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

# 📄 PROMPT

### 🔹 Strategy Hardening Prompt

```
You are tasked with preparing trading strategies and watchers
for hedge-grade optimization and live trading.

Objective:
Validate and harden strategy logic BEFORE any dynamic parameter system.

Rules:
- Disable all hyperopt, drift, retune, volatility scaling (Temporary).
- Focus only on static correctness and trade activity.
- Strategy must trade without optimization.
- Watchers must trigger in real historical conditions.

Steps:
1. Validate each strategy and watcher independently:
   - Trigger frequency
   - Signal relevance
   - Noise ratio
2. Validate strategy activity:
   - Minimum trades per 6 months
   - Works across at least 3 market regimes
3. Enforce minimum activity constraints.
4. Run stress tests by manually perturbing parameters.
5. Reject any strategy that requires optimization to function.
6. Produce a report explaining:
   - Why the strategy trades
   - When it should not trade
   - Failure modes

Output:
- A list of strategies marked as:
  [REJECTED], [NEEDS REVISION], or [OPTIMIZATION-ELIGIBLE]
- Diagnostic metrics for each watcher and strategy.
```

---

# 🧠 Final Summary (Very Important)

* ✔️ Yes — fixing Strategy and Watcher is the **absolute first step**
* ❌ Dynamic parameters before that are **dangerous**
* ✔️ When a strategy works without optimization
  → optimization finally becomes meaningful

---

---

## Priority Stack — Clear, Linear, and Non-Overlapping

Each phase has:

* A clear goal
* A measurable output
* A strict entry condition for the next phase

---

# 🥇 Official Priority Order (Non-Negotiable)

> **If you break this order, the system will either overfit or fail silently**

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

## **Priority 1 — Watcher Hardening**

* Trigger frequency analysis
* Noise ratio
* Market relevance
* Reject dead or over-noisy watchers

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

## **Priority 3 — Strategy Readiness Gate**

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

---

## **Priority 6 — Canary Live**

**Goal:** Real-world execution proof.

* Capital ≤ 20%
* Minimum trade SLA
* No manual intervention

📌 Output:

> Promote / Rollback / Inconclusive

---

## **Priority 7 — Dynamic Systems (Last Step)**

Only now do we ensure:

* The strategy is truly alive

---

# 🧠 Simple Mental Model

```
Watcher → Engine → Fusion → Strategy → Broker
```

---

# ❌ The Most Dangerous Common Mistake

> “The strategy doesn’t trade, let’s optimize it.”

This is **exactly backward**.

---

# 🧩 Final Takeaway

* ✔️ Strategy must be alive first
* ✔️ Optimization is just polish
* ✔️ Dynamic systems are the final layer
* ❌ Nothing can save a broken strategy

---





## All Critical Rules Implemented

### **1. Architectural Compliance**

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
* [ ] Prevent performance degradation or lag.
* [ ] Avoid look-ahead issues and misalignment.
* [ ] Validate all migrated features behave exactly as before.
* [ ] Ensure all code follows best practices and architectural rules.
* [ ] Keep the code DRY (no logic repetition).
* [ ] Verify that the project builds successfully.
* [ ] Ensure all automated tests pass.
* [ ] Perform a final full-system verification to guarantee 100% correctness.
