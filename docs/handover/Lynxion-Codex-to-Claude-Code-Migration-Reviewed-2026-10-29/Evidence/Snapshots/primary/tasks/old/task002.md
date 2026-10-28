# Lynxion ETS — Task0047

# P1.1 Implementation: Real-Time Short-Side Liquidity Safety Gate

## ROLE

Act as:

* Principal Trading Systems Engineer
* Senior Algorithmic Trading Engineer
* Crypto Futures Execution Specialist
* Production Safety Engineer

You are implementing the explicitly approved P1.1 fix from:

`task0046-p1.1-causal-validation-report.md`

---

# AUTHORIZATION

**P1.1 IS EXPLICITLY APPROVED FOR IMPLEMENTATION.**

Approved instruction:

> **APPROVED — implement P1.1**

This is a narrowly scoped production fix.

Do NOT interpret this approval as permission to modify unrelated profitability, strategy, risk, execution, SL/TP, sizing, confidence, regime, or architecture logic.

---

# OBJECTIVE

Implement:

> **Real-Time Liquidity & Short-Side Safety Gate**

The gate must prevent **SHORT entries** when the symbol does not satisfy the approved liquidity condition.

Approved threshold:

> **24h volume > 10,000,000 USDT**

The gate must operate using information available **at decision/order-submission time**.

---

# CRITICAL SCOPE

P1.1 applies ONLY to:

> SHORT entry authorization.

P1.1 MUST NOT modify:

* LONG entries
* existing LONG positions
* existing SHORT positions
* SL calculation
* TP calculation
* SL/TP distance validation
* position sizing
* leverage
* risk percentage
* confidence calculation
* confidence thresholds
* regime detection
* strategy signal generation
* strategy scoring
* strategy parameters
* strategy ranking
* symbol discovery
* market data generation
* execution price calculation
* fill handling
* broker reconciliation
* exit management
* MARKET exits
* STOP_MARKET behavior
* order retry logic
* architecture
* broker abstractions
* LiveExecutionGuard semantics

Do NOT redesign the architecture.

Do NOT create new abstractions unless absolutely required by the existing architecture and strictly limited to this gate.

Prefer the smallest possible production change.

---

# MANDATORY FIRST STEP — READ BEFORE EDITING

Before modifying anything, read:

* `task0046-p1.1-causal-validation-report.md`
* `task0045-profitability-root-cause-audit.md`
* relevant task history
* current implementation of:

    * StrategyAdapters
    * StrategyManager
    * EnterpriseRiskManager
    * BrokerExecutionService
    * MultiBrokerExecutionService
    * LiveExecutionGuard
    * symbol metadata / market-data providers
    * any existing liquidity or volume utilities

Trace the complete current SHORT order path:

```
Strategy Signal
    ↓
Strategy Adapter
    ↓
Strategy Manager
    ↓
Risk Enforcement
    ↓
Execution Authorization
    ↓
Broker Execution
    ↓
Exchange
```

Determine the earliest architecturally correct point where a SHORT-only liquidity gate can be enforced.

Do NOT place the same gate in multiple layers.

Do NOT create multiple competing implementations.

---

# APPROVED FORMULATION

The intended rule is:

```
IF direction == SHORT
    AND real-time 24h volume <= 10,000,000 USDT
THEN
    BLOCK SHORT ENTRY
```

Otherwise:

```
ALLOW existing flow unchanged
```

For LONG:

```
ALWAYS preserve existing behavior.
```

Equivalent conceptual behavior:

```
LONG
  → existing pipeline unchanged

SHORT + volume > 10M
  → existing pipeline unchanged

SHORT + volume <= 10M
  → reject before order submission
```

---

# IMPORTANT: DO NOT USE HISTORICAL DATA

Task0046 established:

> Historical 24h volume was not persisted in `trade_features.csv` (0/610 rows).

Therefore:

* Do NOT reconstruct historical volume.
* Do NOT add fake historical volume values.
* Do NOT modify the historical dataset.
* Do NOT use the 610-trade dataset as a runtime liquidity source.
* Do NOT claim that historical trades were blocked by this rule during the original dataset period.

P1.1 is a **forward-looking real-time production gate**.

---

# REAL-TIME VOLUME SOURCE

Identify the existing authoritative runtime source for 24h volume.

Prefer an already-existing market-data / exchange metadata path.

Before implementation, prove:

1. Where the 24h volume comes from.
2. Which exchange/market it represents.
3. Its units.
4. Its timestamp/freshness semantics.
5. Whether it is available before order submission.
6. Whether it can be safely used by the execution decision path.

Do NOT silently substitute:

* candle volume
* quote volume from another exchange
* estimated volume
* stale cached data
* historical CSV values
* Binance volume for a BingX-specific decision

unless the existing architecture explicitly defines that source as authoritative.

If the current system does not have an authoritative real-time 24h USDT volume source, STOP before implementation and report the blocker.

Do not invent a data source.

---

# FAIL-SAFE BEHAVIOR

This is a production safety gate.

Define explicit behavior for:

* volume unavailable
* volume = null
* volume = 0
* malformed volume
* NaN
* infinity
* stale volume
* API failure
* timeout
* exchange metadata unavailable
* unsupported symbol
* unit conversion failure

Do NOT silently treat unknown liquidity as:

> volume > 10M

Do NOT fail open by default.

The safety behavior must be consistent with the existing production risk/execution safety philosophy.

However:

**Do not redesign global failure semantics.**

Only implement the minimum behavior necessary for P1.1.

Document the chosen behavior and why it is safe.

---

# SHORT DETECTION

Use the existing canonical representation of order direction.

Do NOT introduce a second definition of:

* LONG
* SHORT
* BUY
* SELL

Verify how the current system maps:

```
BUY ↔ LONG
SELL ↔ SHORT
```

and use the existing canonical representation.

Do not infer direction from unrelated fields.

---

# SYMBOL HANDLING

Do NOT hardcode the eight historical symbols as the primary production rule:

* SEIUSDT
* UNIUSDT
* LDOUSDT
* AVAXUSDT
* SUIUSDT
* XLMUSDT
* NCCOGOLD2USDUSDT
* SOLUSDT

The approved formulation is a **dynamic liquidity gate**.

These eight symbols are forensic evidence explaining why the gate is needed, NOT necessarily a production blacklist.

Do not create:

```text
BLOCK_SHORT_SYMBOLS = [...]
```

unless existing architecture requires a temporary compatibility mechanism and this is explicitly proven necessary.

The intended production behavior is:

> evaluate current real-time liquidity for the current symbol.

---

# ORDER PATH REQUIREMENT

The gate must execute BEFORE the SHORT order can reach the exchange.

Prove that a rejected SHORT cannot bypass the gate through:

* another strategy adapter
* another StrategyManager path
* direct broker calls
* alternate execution services
* retry logic
* emergency execution paths
* paper/live divergence
* any other existing order-placement path

Do not create a new bypass-prone path.

---

# ARCHITECTURAL CONSTRAINT

The existing architecture is frozen.

Do NOT:

* redesign StrategyManager
* redesign execution
* introduce a new risk framework
* introduce a new broker abstraction
* create a second execution pipeline
* move order placement
* restructure strategy adapters
* refactor unrelated code
* rename unrelated interfaces
* perform broad cleanup

Only make the smallest change required to implement P1.1 correctly.

---

# LOGGING / OBSERVABILITY

A blocked SHORT must produce an auditable event.

At minimum capture:

* symbol
* direction
* current 24h volume
* threshold
* gate decision
* reason
* timestamp

Example conceptual reason:

```text
SHORT_BLOCKED_LIQUIDITY
```

Do NOT log sensitive information unnecessarily.

Do NOT alter unrelated telemetry.

Ensure that a blocked order is clearly distinguishable from:

* strategy rejection
* risk rejection
* broker rejection
* exchange rejection

---

# NO FALSE ORDER JOURNAL ENTRIES

A P1.1-blocked SHORT is an authorization rejection.

It must NOT be recorded as:

* exchange order
* submitted order
* filled order
* completed trade
* broker execution

unless the existing architecture explicitly records rejected intents separately.

Do not corrupt trade accounting.

---

# TESTING REQUIREMENTS

Before declaring completion, add/update the smallest necessary tests.

At minimum prove:

### Test 1 — LONG unaffected

Given:

```text
direction = LONG
volume <= 10M
```

Result:

```text
existing LONG behavior preserved
```

---

### Test 2 — SHORT above threshold

Given:

```text
direction = SHORT
volume > 10M
```

Result:

```text
SHORT allowed
existing execution flow preserved
```

---

### Test 3 — SHORT exactly at threshold

Given:

```text
direction = SHORT
volume = 10,000,000
```

Result:

```text
SHORT BLOCKED
```

The comparison must be explicitly documented as:

```text
> 10M = allowed
<= 10M = blocked
```

---

### Test 4 — SHORT below threshold

Given:

```text
direction = SHORT
volume < 10M
```

Result:

```text
SHORT BLOCKED
```

---

### Test 5 — Missing volume

Given:

```text
direction = SHORT
volume = unavailable
```

Verify the documented safety behavior.

---

### Test 6 — Invalid volume

Test:

* null
* NaN
* infinity
* negative value
* malformed value

Verify safe behavior.

---

### Test 7 — No exchange submission

For blocked SHORT:

```text
authorize → reject
exchange submission count = 0
```

Prove that no broker order is sent.

---

### Test 8 — No LONG regression

Verify that P1.1 does not alter:

* LONG authorization
* LONG sizing
* LONG SL/TP
* LONG execution

---

### Test 9 — Existing high-liquidity SHORT

Use a valid >10M volume case and prove the complete existing SHORT execution path remains unchanged.

---

### Test 10 — Bypass-path test

Attempt to exercise every known SHORT entry point and verify that the P1.1 gate cannot be bypassed.

---

# REGRESSION REQUIREMENTS

Run the existing relevant test suite.

Do NOT modify unrelated failing tests merely to obtain a green build.

If unrelated tests fail:

* report them separately
* identify whether they pre-existed
* do not hide them

Verify specifically that P1.1 does not alter:

* SL/TP
* risk enforcement
* position sizing
* confidence
* regime
* execution guard
* broker order creation
* reconciliation

---

# STATIC CODE VERIFICATION

After implementation, inspect the source again.

Prove:

1. P1.1 has exactly one authoritative enforcement point.
2. LONG is unaffected.
3. SHORT above threshold is unaffected.
4. SHORT at/below threshold is blocked.
5. Blocked SHORT cannot reach broker submission.
6. No alternative execution path bypasses the gate.
7. No unrelated production logic changed.

Use code evidence with file names, classes, methods, and relevant line ranges.

---

# DIFF AUDIT

Before completion:

* inspect `git diff`
* inspect changed files
* inspect changed methods
* confirm scope is minimal

Explicitly report:

```text
Files modified:
Files added:
Files deleted:
Unrelated files changed:
```

If unrelated files changed, investigate and revert them if they are not required.

Do not leave incidental refactoring in the patch.

---

# REQUIRED FINAL REPORT

Create:

`task0047-p1.1-implementation-report.md`

The report must contain:

## 1. Implementation Summary

What changed and why.

## 2. Enforcement Point

Exact class/method/path where P1.1 is enforced.

## 3. Runtime Volume Source

Exact source, units, freshness, and availability.

## 4. Rule

Explicitly state:

```text
SHORT + 24h volume <= 10M USDT → BLOCK
SHORT + 24h volume > 10M USDT → ALLOW
LONG → unchanged
```

## 5. Fail-Safe Behavior

Document behavior for unavailable/invalid/stale volume.

## 6. Bypass Analysis

Enumerate all known SHORT execution paths and prove the gate cannot be bypassed.

## 7. Test Results

Provide exact results.

Format:

| Test                 | Result    | Evidence |
| -------------------- | --------- | -------- |
| LONG unaffected      | PASS/FAIL |          |
| SHORT >10M           | PASS/FAIL |          |
| SHORT =10M           | PASS/FAIL |          |
| SHORT <10M           | PASS/FAIL |          |
| Missing volume       | PASS/FAIL |          |
| Invalid volume       | PASS/FAIL |          |
| No broker submission | PASS/FAIL |          |
| Bypass paths         | PASS/FAIL |          |
| Regression suite     | PASS/FAIL |          |

## 8. Regression Verification

Explicitly verify:

* SL/TP unchanged
* Risk unchanged
* Position sizing unchanged
* Confidence unchanged
* Regime unchanged
* Execution architecture unchanged

## 9. Git Diff Audit

Report exact scope of changes.

## 10. FACT / INFERENCE / UNKNOWN

Classify implementation conclusions.

---

# STOP CONDITION

After implementation and verification:

**DO NOT implement any additional optimization.**

Do NOT:

* add symbol blacklists
* disable all SHORTs
* tune the 10M threshold
* change SL/TP
* modify risk
* change confidence
* change strategies
* modify regime logic
* optimize profitability further

STOP after producing:

`task0047-p1.1-implementation-report.md`

Wait for explicit approval for the next phase.

Final status must be one of:

> IMPLEMENTED AND VERIFIED — AWAITING POST-IMPLEMENTATION GATE

or

> IMPLEMENTATION BLOCKED — EVIDENCE/ARCHITECTURAL ISSUE FOUND
