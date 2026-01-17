First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

### **Task Description – Architecture & Flow Correction**

During code review, I identified **architectural violations in the decision flow**, especially within the **Watcher layer**.
Some responsibilities such as **risk management and SL/TP calculation are implemented multiple times across different layers**, instead of being **centralized and invoked only from the Strategy layer**.

This breaks **strategy ownership**, causes **hidden coupling**, and explains why **signals are generated but no trades are executed**.

#### **Required Actions**

* Review **logs (`./logs`) and source code** to identify:

  * Why signals are approved/rejected without transparent reasons
  * Why no symbol reaches order placement after initial evaluation
* Ensure each layer strictly follows its **single responsibility**:

  * **Watchers** → only emit raw market observations
  * **Engine** → interpret signals (direction, strength, confidence)
  * **Fusion** → aggregate signals and determine market bias
  * **Strategy** → *only place where strategy selection, risk management, and SL/TP calculation are allowed*
  * **Broker** → execution-only, no decision logic
* **Remove duplicated risk / SL / TP logic** from non-strategy layers
* Ensure **Risk Manager is called only by Strategy**
* Validate that the full flow
  **Watcher → Engine → Fusion → Strategy → Broker**
  works end-to-end without architectural leakage

#### **Deliverables**

* A **concise report** explaining:

  * Where the architecture is violated
  * Why trades are not placed
  * Which logic must be removed, centralized, or rewired
* A **log analysis report** explaining signal rejection / acceptance
* A corrected flow that preserves **Hexagonal Architecture, SOLID principles, and DRY**

> The goal is to **fix the system without breaking the architecture**, restore correct ownership of decisions, and enable reliable trade execution.

