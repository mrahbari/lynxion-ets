You are a senior hedge fund systems architect and quantitative trading systems engineer.
I am working with a production-grade, event-driven hedge fund trading system with the following high-level flow:


I recently faced with a major issues, First check the production logs which is located in ./logs/* , then try to understand the below analysis result.
In reality, there is no successful order placements which I worry about it!
-Also, after changes you need to cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

```
Watcher → Engine → Fusion → Strategy → Broker
```

The system is fully event-driven and orchestrated.

---

## Expected System Behavior

* Watchers identify and emit candidate trading symbols.
* Each symbol enters a multi-step workflow.
* At every step, the symbol is evaluated using a real-time **confidence metric**, which represents a composite of multiple acceptance conditions.
* If the confidence meets or exceeds the configured threshold for that step, the workflow proceeds.
* Only when **all workflow steps succeed**, a valid trade order must be registered at the broker.

Confidence is not a single rule; it represents a group of acceptance constraints. This assumption must be preserved throughout the analysis.

---

## Observed Issue

Even when the confidence threshold is drastically reduced (e.g., from 60/100 to 5–10/100), the system still fails to register successful broker orders.

This strongly indicates a malfunction in one or more of the following areas:

* Workflow step logic
* Configuration or parameterization
* Orchestration or event propagation
* Fusion weighting or gating
* Strategy decision constraints
* Broker integration or order lifecycle handling

---

## Required Diagnostic Approach

You must analyze the system using **both tracing directions**:

### 1. Backward Trace (Outcome-Driven Debugging)

Start from the Broker layer and trace backwards to determine:

* Whether an order request was ever sent
* Where the last successful state occurred
* Which layer prevented further progression

This approach is critical because the system’s failure is defined by the absence of a final executed trade.

### 2. Forward Trace (Input-Driven Verification)

Start from a single Watcher and trace a symbol forward through:

```
Watcher → Engine → Fusion → Strategy → Broker
```

Validate:

* Event propagation
* State transitions
* Confidence transformation
* Approval / rejection decisions

Both trace directions must converge to the same failure point.

---

## Your Responsibilities

1. Restate and validate the intended system behavior and identify any architectural or logical inconsistencies.
2. Define explicit acceptance criteria and invariants that preserve system stability and architectural integrity.
3. Provide a **step-by-step, low-level tracing and monitoring strategy** using both backward and forward trace methodologies.
4. Propose a structured validation approach for:

   * Configuration and parameters
   * Workflow state transitions
   * Confidence evaluation logic
   * Fusion scoring and gating
   * Event propagation and orchestration
   * Strategy decision constraints
   * Broker order lifecycle
5. Provide a systematic log analysis strategy using logs located in `./logs`, specifying:

   * What to inspect in each layer
   * Which correlations matter
   * How to detect silent failures, dropped events, or state deadlocks
6. Recommend a controlled testing methodology:

   * Activate only one watcher initially
   * Trace its symbol end-to-end with a unique trace identifier
   * Gradually enable additional watchers after correctness is verified

---

## Output Requirements

Your output must be:

* Precise and implementation-oriented
* Suitable for debugging a production-grade hedge fund trading system
* Architecture-safe (must not break the current design)
* Explicit about failure points, not generic or theoretical

The goal is to identify the exact point where symbols stop progressing toward broker execution and to explain why.

Avoid assumptions that any single component is correct by default. Treat every layer as potentially faulty until proven otherwise.
