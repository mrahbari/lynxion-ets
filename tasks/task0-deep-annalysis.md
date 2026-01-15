-Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

I want a **complete, detailed, and professional review** of my entire project.
The final output must include a file named **`./docs/COMPREHENSIVE-ANALYSIS-PRO.<VERSION>.md`** that summarizes all findings.

---

## **1. Scope of the Review**

The review must cover **every part of the project's logic and workflow**, including:

### **Orchestrators**

* Watcher Orchestrator
* Engine Orchestrator
* Strategy Orchestrator
* Any additional orchestrators involved in the data or trading pipeline

### **Workflow Validation**

You must verify that the sequence below is correct, aligned, and fully functional:

```
Watcher → Engine → Fusion → Strategy → Broker
```

If anything is missing, incorrect, inefficient, or buggy, you must fix it or propose an improved implementation.

---

## **2. Strategy & Hyperopt Validation**

### **Strategy Orchestrator**

* Verify that the Strategy Orchestrator works correctly.
* Ensure that all strategies execute as expected.
* Identify any issues, weaknesses, or inconsistencies.
* Provide improvements wherever necessary.

### **Hyperopt**

* Ensure Hyperopt definitions are correct for **all strategies**.
* Validate that Hyperopt parameters, ranges, and configurations follow best practices.
* Identify misalignments or data-leak risks.

---

## **3. Detailed Analysis Requirements**

For **each component, module, strategy, orchestrator, and workflow segment**, provide:

### **a. Strengths**

### **b. Weaknesses**

### **c. Improvement Recommendations**

Improvements must be **specific**, not generic.

---

## **4. Integration Tests**

Review, design, or validate the integration tests that follow this exact sequence:

```
Watcher → Engine → Fusion → Strategy → Broker
```

Tests must ensure full end-to-end functionality, including data flow, signal generation, order execution, and edge-case handling.

---

## **5. Mandatory Standards (Critical & Required)**

All code **must 100% comply** with these standards:

1. **No Lookahead Bias**
2. **No Lag Misalignment**
3. **Proper Indicator Shifting**
4. **No Data Snooping Bias**
5. **No Survivorship Bias**
6. **MTF Sync:**

   * downsample → ffill → shift → align
7. **Stop-Loss / Take-Profit:**

   * Implement using **candle High/Low**, not close
8. **SL Priority > TP Priority for Longs**
9. **Real PnL Calculation:**

   * using real execution price + fees + slippage
10. **Equity Curve Drawdown:**

    * using peak/trough logic
11. **Portfolio Exposure Limits:**

    * must be enforced
12. **No Double Entries (unless explicitly allowed)**
13. **Correct Validation Flow**

---

## **6. Final Deliverable**

At the end of the review, generate a structured and well-written Markdown file:

### **`./docs/COMPREHENSIVE-ANALYSIS-PRO.<VERSION>.md`**

The file must include:

* Full project analysis
* Strengths & weaknesses
* Detailed improvement roadmap
* Architecture insights
* Strategy & Hyperopt validation results
* Workflow verification
* Compliance with mandatory standards
* Testing recommendations
* Any code-level fixes or rewrites

