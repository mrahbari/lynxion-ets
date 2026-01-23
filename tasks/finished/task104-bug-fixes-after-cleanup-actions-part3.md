- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Do the analyzed the existing implementation, identified weaknesses, and implemented all the improvements

You are acting as a senior production trading systems engineer
responding to a live incident.

The system is a crypto scalping hedge-fund-grade platform with
the following architecture:

WATCHER → ENGINE → FUSION → STRATEGY → RISK MANAGER → BROKER

CRITICAL INCIDENT:
The system produces logs and signals, but places ZERO orders
under all market conditions.

---

### DATA ACCESS (MANDATORY)

You MUST analyze the ACTUAL forensic logs stored on disk.

Log location:
- ./logs/
- All JSON logs
- All layers
- All timestamps

Do NOT rely on assumptions or summaries.
All conclusions must be supported by log evidence.

Specifically:
- Search for presence AND absence of events
- Correlate logs using trade_id / trace_id
- Detect where the event chain stops

---

### STEP 1 — END-TO-END LOG TRACE (NON-NEGOTIABLE)

From ./logs, reconstruct the FULL lifecycle of a hypothetical trade:

WATCHER log →
ENGINE log →
FUSION log →
STRATEGY log →
RISK log →
BROKER log →
ORDER PLACED

Answer explicitly:

- Which layer is the LAST one that logs activity?
- Which expected log NEVER appears?
- Is the failure silent or logged?

If a layer has NO logs at all:
- Treat this as a critical failure
- Identify why it is never reached

---

### STEP 2 — BOOLEAN DEADLOCK EXTRACTION

From the code + logs, identify ALL boolean conditions
required for order placement.

For each condition:
- Name it
- Layer
- Expected TRUE case
- Actual observed value in logs

Explicitly identify:
- Conditions that are ALWAYS false
- Conditions that depend on impossible combinations
- Conditions duplicated across layers

---

### STEP 3 — RISK MANAGER HARD BLOCK ANALYSIS

Using logs only:

- Is position_size ever > 0?
- Is risk_amount > 0?
- Is SL distance valid after leverage?
- Is division by (entry - SL) collapsing size to zero?
- Is max_risk_per_trade effectively zero?

If RISK rejects:
- Show the exact rejection reason
- Show why it rejects 100% of cases

If RISK logs do NOT exist:
- Treat as a fatal implementation bug

---

### STEP 4 — BROKER SILENT REJECTION CHECK

From ./logs:

- Search for ANY broker validation failures
- Check duplicate prevention triggers
- Check exposure / margin checks
- Check order submission attempts

If BROKER logs exist without ORDER PLACED:
- Identify missing transition
- Identify missing error logging

If no BROKER logs exist:
- Identify why order intent never reaches broker

---

### STEP 5 — MINIMUM VIABLE TRADE PATH (UNLOCK MODE)

Define the ABSOLUTE MINIMUM conditions required
for ONE order to be placed:

- One watcher
- One engine
- One fusion signal
- One strategy decision
- One risk approval
- One broker submission

Everything else must be temporarily bypassed or logged-only.

If even this path fails:
- State explicitly that the system is logically deadlocked
- Identify the exact code location responsible

---

### REQUIRED OUTPUT (STRICT)

1. LAST LOG SEEN PER TRADE PATH
   - File
   - Layer
   - Timestamp
   - trade_id

2. EXACT BLOCKING CONDITION
   - Boolean expression
   - Code location
   - Why it is never satisfied

3. MINIMAL FIX PLAN
   - Max 5 changes
   - Remove or relax logic
   - No new features
   - No architecture changes

4. POST-FIX VERIFICATION STEPS
   - Which logs must appear
   - In what order
   - What confirms the fix worked

---

### HARD CONSTRAINTS

- No new indicators
- No new strategies
- No new risk rules
- No ML
- No refactors

This is NOT optimization.
This is SYSTEM RECOVERY.

Treat missing logs as bugs.
Treat silent failures as critical defects.
