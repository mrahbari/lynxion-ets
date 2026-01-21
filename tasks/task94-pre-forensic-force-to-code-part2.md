- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Take a look at ./logs/forensic.log which is already implemented and the history of successful order placement is there! 
- Review the implemented codes specially ./infrastructure/logging/forensic_logger.py for more clarification.

---

# Reality Check From Your Logs

Your logs prove:

* You **log everything** ✔
* But almost everything is **statistically indefensible** ❌
* Decisions are being made while:

  * sample_size = 1…5
  * no contributor diversity
  * no fusion value addition
  * no strategy OOS validation
  * no evidence accumulation

So:

> Your system is **observable**, but NOT YET **scientifically accountable**.

That is exactly what PRE-FORENSIC and FORENSIC must fix.

---

# What PRE-FORENSIC Must Finish

PRE-FORENSIC is **NOT about trading performance**.
It is about **decision accountability readiness**.

PRE-FORENSIC is complete only when:

| Requirement                                        | Status    |
| -------------------------------------------------- | --------- |
| Every decision has a traceable causal chain        | ✅         |
| Every decision has statistical defensibility score | ⚠ partial |
| Every decision has randomness exposure flag        | ⚠ partial |
| Every decision can be rejected automatically       | ❌         |
| Every decision has minimum evidence gate           | ❌         |
| Every decision has maturity level                  | ❌         |
| Every layer can veto downstream layers             | ❌         |
| Every trade has a defensibility grade              | ❌         |

You are missing **decision governance**, not logging.

---

# What FORENSIC Phase Means

FORENSIC =

> "We only optimize what is statistically and causally proven."

No confidence.
No belief.
No intuition.

Only:

* Evidence accumulation
* Decision maturity
* Causal attribution
* Regret analysis
* Counterfactual analysis
* Responsibility allocation

---

# What You Should Ask Next (Instruction to the System)

You must now **command** the system to:

1. Stop accepting statistically immature signals
2. Stop allowing fusion without contributor diversity
3. Stop allowing strategies without OOS evidence
4. Stop allowing trades without defensibility grade
5. Start labeling every trade as:

   * SCIENTIFIC
   * PROBATIONARY
   * RANDOM

---

# FINAL MASTER PROMPT

(Use this EXACTLY. Do not soften it.)

---

## 🔴 MASTER PROMPT — PRE-FORENSIC & FORENSIC FINALIZATION

```
You are now acting as a Hedge Fund Forensic Architecture Auditor.

Your task is NOT to describe, summarize, or praise the system.

Your task is to:

1. Identify where the system is still making decisions with insufficient statistical authority.
2. Identify where decisions are not causally defensible.
3. Identify where the system is exposing capital to randomness.
4. Identify where logging exists but governance does not.

You must produce:

A) A PRE-FORENSIC COMPLETION CHECKLIST
   - Exact missing decision gates
   - Exact missing rejection rules
   - Exact missing maturity thresholds
   - Exact missing statistical accumulation requirements

B) A FORENSIC READINESS SPECIFICATION
   - What qualifies a signal as "scientifically tradable"
   - What disqualifies a trade automatically
   - What evidence must exist before capital deployment

C) A DECISION DEFENSIBILITY SCORING MODEL
   - Inputs
   - Weighting logic
   - Output interpretation

D) A RANDOMNESS EXPOSURE CONTROL SYSTEM
   - How to quantify randomness
   - How to block randomness-based trades
   - How to downgrade system confidence automatically

E) A TRADE CLASSIFICATION SYSTEM
   - SCIENTIFIC
   - PROBATIONARY
   - RANDOM
   - With rules and thresholds

F) A FORENSIC ATTRIBUTION MODEL
   - How loss is assigned to watcher / engine / fusion / strategy / execution
   - How responsibility is distributed

G) A FORENSIC OPTIMIZATION PIPELINE
   - What is optimized first
   - What is forbidden to optimize
   - What is evidence-gated

You must NOT write any code.

You must NOT rewrite architecture.

You must NOT describe existing logs.

You must define what is missing for the system to become scientifically and institutionally defensible.

Be brutally honest.
Be mathematically strict.
Be hedge-fund-grade.

Assume the system will manage 9-figure capital and must survive regulatory, legal, and investor forensic audits.

Do not beautify. Do not simplify.

Only truth, structure, and enforcement.
```

---

# What This Will Produce

If the model answers correctly, you will receive:

* A **decision governance layer** above your architecture.
* A **scientific firewall** before capital deployment.
* A **forensic spine** for the entire fund.
* A system that no longer trades on belief.

---

# Your Current System Status

Honest assessment:

> You built an **institutional-grade observability system**.
> You have NOT yet built an **institutional-grade decision governance system**.

That is normal.
That is exactly where real hedge funds separate from retail systems.

---


When you run that prompt and bring me the result and give me:
* Map it directly onto my architecture
* Convert it into enforceable layers
* Tell me exactly which parts must be implemented first
* And only then… I enter **true Hedge Fund Forensic Optimization**


