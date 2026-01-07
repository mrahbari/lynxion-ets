
> When I want to send my order to BingX, I hit a rate limit issue.
> I think there is a fundamental problem somewhere.
> According to the flow below, the watchers track symbols, and this process continues until the symbol reaches the strategy.
>
> I think we should apply the following items to the system:
>
> 1. We should specify which broker each watcher uses to read data from. Currently, Binance and BingX are active, and Phemex and MEXC will be activated soon. So we should define via configuration (.env, .env.example) which broker to use. The default is Binance. 
> 2. Check how many times timeframe data is fetched from the broker when symbols are checked in different flows. Logically, the 1-minute timeframe should be fetched once for a specific time window and then reused in the next steps, so we don’t hit rate-limit issues.
>
> I don’t have enough knowledge to propose a better solution to solve the rate-limit problem. If you can fix the issue with a better approach, please do so.
> Because the system is used at large scale and is a hedge fund, following standards is the most important principle.

So that in the next step, we can begin precise corrections and finalize the project.
Also give me a specific report about the review of logs and try to have some successful trades through flow!
I need to have some successful orders!

## Decision Flow, Strategy Ownership & Architecture Audit

---

## 1️⃣ Canonical Hedge Fund Decision Flow
```
Watcher → Engine → Fusion → Strategy → Broker
```

Each layer has **strict decision boundaries**.
Violating these boundaries creates **hidden risk, broken risk ownership, and non-reproducible behavior**.

---


## Extra Critical Rules Implemented

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

