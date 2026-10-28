- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Take a look at ./logs/forensic.log which is already implemented and the history of successful order placement is there! 
- Review the implemented codes specially ./infrastructure/logging/forensic_logger.py for more clarification. 

Now, It's time to carefully read the below description and requirement and do your best to handle it! 



---

# 🔹 FINAL PROMPT — PRE-FORENSIC INSTITUTIONAL COMPLETION AUDIT

You are a hedge-fund forensic trading system auditor.

Your task is NOT to praise architecture.
Your task is to expose everything that prevents this system from being statistically defensible, auditable, and institutionally reliable.

The system uses a multi-layer architecture:

WATCHER → ENGINE → FUSION → STRATEGY → BROKER → BROKER_CLOSE

Structured JSON logging is implemented.

However, I want you to assume:

> “The system is potentially wrong, and must prove that it is right.”

---

## Your Mission

Perform a **Pre-Forensic Institutional Completion Audit**.

You must:

1. Identify **exact missing log fields** per layer.
2. Identify **where statistical evidence is insufficient**.
3. Identify **where decisions are not defensible mathematically**.
4. Identify **where the system is effectively gambling instead of trading**.
5. Identify **where loss attribution cannot be proven**.
6. Identify **where correlation, regime, or confidence is not operationally enforced**.
7. Identify **where duplicate trade prevention is architectural vs accidental**.
8. Identify **where logging exists but is not analytically usable**.

You are NOT allowed to assume correctness.

---

## Required Output Structure

You MUST output the audit in the following structure.

---

### 1. Layer-by-Layer Forensic Weakness Map

For each layer:

WATCHER
ENGINE
FUSION
STRATEGY
BROKER
BROKER_CLOSE

Provide:

• What statistical proof is missing
• What decision cannot be defended
• What randomness is not controlled
• What cannot be reconstructed later

Example format:

Layer: ENGINE
Missing statistical proof:
Missing decision defensibility:
Randomness exposure:
Reconstruction risk:

---

### 2. Mandatory Logging Fields To Add

For each layer, list:

Field name
JSON type
Why this field is mandatory at hedge-fund level
What failure it prevents
What analysis it enables

No generic reasons. Only operational.

---

### 3. Capital Risk Exposure Map

Identify exactly where capital is currently exposed to:

• Noise instead of signal
• Correlation illusion
• Regime misclassification
• Confidence inflation
• Execution randomness
• Strategy over-trust

Explain how each one can cause real loss.

---

### 4. Decision Defensibility Test

For a single trade, explain:

Which parts of the decision are mathematically provable
Which parts are heuristic
Which parts are statistically unsupported
Which parts are effectively belief-based

Label each part clearly.

---

### 5. Statistical Authority Score

Assign a score from 0–10 for:

Watcher reliability
Engine interpretation reliability
Fusion statistical validity
Strategy capital logic reliability
Execution reliability

Explain exactly why.

---

### 6. Randomness Exposure Index

List all components that currently behave probabilistically without control:

Example:

• Fusion dominance tie
• Regime boundary
• Strategy filter conflict
• Broker slippage variance

Explain how to log and control each.

---

### 7. Logging Architecture Upgrade Plan

Now — and only now — propose:

Exact JSON log schemas to add
Exact fields
Exact placement in architecture
Exact naming
Exact reason

Each schema must include:

trace_id
layer
timestamp
exchange
symbol

Plus new forensic fields.

---

### 8. Final Institutional Verdict

Classify the system strictly as:

Not Forensic Ready
Pre-Forensic
Forensic Candidate
Forensic Validated

And justify the classification without emotion.

---

## Absolute Rules

• Do not praise architecture
• Do not assume intent
• Do not comfort
• Do not soften language
• Do not avoid uncomfortable conclusions

Your role is to protect capital, not ego.

---

## Goal

The goal is NOT to make the system look good.

The goal is to make it **survivable under audit, drawdown, and capital scale.**

---

## Closing Instruction

If any part of the system cannot be statistically defended, you MUST say so explicitly.

If any decision depends on hope, you MUST label it as hope.

If any profit cannot be reconstructed, you MUST mark it as untrustworthy.

---

# 🔹 END PROMPT

