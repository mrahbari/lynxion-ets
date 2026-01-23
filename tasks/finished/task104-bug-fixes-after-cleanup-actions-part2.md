- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Do the analyzed the existing implementation, identified weaknesses, and implemented all the improvements

You are a senior quantitative trading systems engineer tasked with
recovering a production crypto scalping system that has become inactive
after multiple optimizations.

The system architecture includes:
- WATCHERS (market perception)
- ENGINES (signal interpretation)
- FUSION (multi-engine aggregation)
- STRATEGIES (entry/exit logic)
- RISK MANAGER (position sizing, SL/TP)
- BROKER (execution)

The system currently produces forensic logs but has not executed
any successful trades in the last 24 hours.

Your task is NOT to add new features or rewrite the system.
Your task is to IDENTIFY and RESOLVE blocking logic using forensic logs only.

---

### OBJECTIVES

1. Analyze the forensic logs and identify:
   - Where signals are being rejected
   - Which layer acts as the primary bottleneck
   - Whether rejection is due to confidence, regime mismatch,
     risk constraints, or fusion indecision

2. For each layer (Watcher, Engine, Fusion, Strategy, Risk):
   - Identify implicit assumptions
   - Detect over-filtering or redundant logic
   - Highlight conflicting rules across layers

3. Specifically analyze:
   - Regime classification vs selected strategies
   - Fusion confidence distribution over time
   - Strategy filter pass/fail ratios
   - Risk manager rejection reasons
   - SL/TP feasibility given entry price and volatility

---

### REQUIRED OUTPUT (STRICT)

Produce the following sections:

#### 1. SYSTEM BLOCKAGE MAP
- Layer-by-layer identification of where trades are stopped
- Quantified rejection ratios per layer

#### 2. EXPECTANCY IMPACT ANALYSIS
- How each rejection affects real expectancy
- Identify which filters reduce expectancy instead of improving it

#### 3. MINIMAL FIX STRATEGY (CRITICAL)
- Propose the MINIMUM set of changes required
- Explicitly state:
  - Which logic should be relaxed
  - Which thresholds should be adaptive
  - Which checks are redundant and can be removed
- NO new indicators
- NO new ML
- NO architectural changes

#### 4. RISK-FIRST REALIGNMENT
- Ensure SL/TP, position sizing, and leverage are aligned
- Validate that trades rejected by risk are truly negative expectancy
- Flag cases where the risk manager blocks profitable trades

#### 5. FINAL VERDICT
- Is the system inactive due to:
  a) Over-filtering
  b) Regime misalignment
  c) Risk paralysis
  d) Fusion indecision
  e) Combination of the above

---

### CONSTRAINTS

- Do NOT propose adding new code modules
- Do NOT increase system complexity
- Do NOT optimize for backtest appearance
- Optimize ONLY for:
  - Real execution
  - Scalping feasibility
  - Sustainable expectancy

Your response must be technical, concrete, and actionable.
Avoid generic trading advice.
Base all conclusions strictly on forensic log evidence.
