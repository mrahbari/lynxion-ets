I want a **complete, detailed, and professional review** of my entire watchers.
The final output must include a file named **`./docs/COMPREHENSIVE-ANALYSIS-WATCHERS.<VERSION>.md`** that summarizes all findings.

---

## **1. Scope of the Review**

The review must cover **every part of the watchers' logic  in infrastructure/watchers:

### **Workflow Validation**

You must verify that the sequence below is correct, aligned, and fully functional:

```
Watcher → Engine → Fusion → Strategy → Broker
```

If anything is missing, incorrect, inefficient, or buggy, you must fix it or propose an improved implementation.

---

## **2. Strategy Validation**

### **Strategy Orchestrator**

* Verify that the Strategy Orchestrator works correctly.
* Ensure that all watchers execute as expected.
* Identify any issues, weaknesses, or inconsistencies.
* Provide improvements wherever necessary.


---

## **3. Detailed Analysis Requirements**

For **each strategy, orchestrator, and workflow segment**, provide:

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
7. **Equity Curve Drawdown:**
    * using peak/trough logic
8. **Portfolio Exposure Limits:**
    * must be enforced
9. **No Double Entries (unless explicitly allowed)**
10. **Correct Validation Flow**

---

## **6. Final Deliverable**

At the end of the review, generate a structured and well-written Markdown file:

### **`./docs/COMPREHENSIVE-ANALYSIS-WATCHERS.<VERSION>.md`**

The file must include:

* Full project analysis
* Full strategy analysis
* Strengths & weaknesses
* Detailed improvement roadmap
* Architecture insights
* Workflow verification
* Compliance with mandatory standards
* Testing recommendations
* Any code-level fixes or rewrites

