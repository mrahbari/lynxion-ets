I think now we need to do a review of the project from start to finish and you should give me your assessment.
In fact, in our architecture we have **watchers**. They find the coins, and after the engines are evaluated, **fusion** passes the results to the strategies.
Our plan is to use our strategies to decide if a coin has potential and then finalize it and send it to the broker to place a buy or sell order.

At the same time, we want to have **strong backtesting and walk-forward testing** so that we can optimize our strategies using **Hyperopts**.
We need to **download coin history** for a specific time period, in a time frame suitable for scalping, and run enough backtests so that the Hyperopts are correctly tuned.

We need **re-tuning** for old Hyperopts.
We also need to **create Hyperopts for coins that the watchers find**, and if there is no existing Hyperopt for a coin, use default values and then update the Hyperopt later.
We also need **rate limits** for watchers, strategies, and so on.

These are the things I can remember right now.
You need to review and see what the current status really is.
Can we make a plan to **test and cover all these points**, reach a **stable point**, and then move on to **live testing**?

Please **start professionally from beginning to end**, and give me a **report**.
Then provide a **detailed report of the system functionality**, including things I may have forgotten, so I can read it and get a complete view of the system.

You can create **documentation for reporting, test instructions for each part, testing each section, etc.**
You could even virtually **update the code**, or suggest **bug fixes or updates in a separate README file** so we can review and apply them.

---

I want a **complete, detailed, and professional review** of my entire project.
The final output must include a file named **`COMPREHENSIVE-ANALYSIS-PRO.md`** that summarizes all findings.

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

### **`COMPREHENSIVE-ANALYSIS-PRO.md`**

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

