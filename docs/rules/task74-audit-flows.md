First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

You did some changes in infrastructure/watchers/market_opportunity_watcher.py and other places, so verify correct implementation**.

###  1 — Watcher Audit

```
Verify that the Watcher layer:
- Produces only market observations or raw signals
- Does NOT assign BUY or SELL
- Does NOT select or reference any strategy
- Does NOT define SL/TP
- Does NOT create or submit orders

If any of the above are violated, flag an architecture breach.
```

---

###  2 — Engine Audit

```
Verify that the Engine:
- Interprets raw signals
- Assigns strength and confidence only
- Does NOT trigger execution
- Does NOT select strategy
```

---

###  3 — Fusion Audit

```
Verify that Fusion:
- Aggregates interpreted signals
- Produces dominance or HOLD states
- HOLD is contextual and reversible
- Contains no strategy or capital logic
```

---

###  4 — Strategy Audit (Critical)

```
Verify that Strategy:
- Is the ONLY layer selecting strategies
- Accepts or rejects fused signals
- Calls Risk Management
- Produces execution intent only after approval
```

---

###  5 — Broker Audit

```
Verify that Broker:
- Receives fully-formed orders
- Rejects orders without SL and TP
- Does NOT modify intent or strategy
```

---

## 7️⃣ Final Institutional Conclusion

Your concern is **100% valid**.

If strategy selection happens in the Watcher:

* The architecture is compromised
* Risk control is illusionary
* Scaling the system will fail

> **Even if the system “works”, it is structurally unsafe.**

