# Lynxion ETS — Phase 3.1
# Trade Lifecycle Extension Audit
# Auto Breakeven & Trailing TP/SL Verification

You are performing a production trading lifecycle audit.

Do NOT redesign architecture.

Do NOT add unnecessary abstractions.

Do NOT implement blindly.

First determine the current capability, missing parts, and production risks.

==================================================

OBJECTIVE

Verify whether Lynxion ETS correctly manages an open trade AFTER entry.

The audit scope:

Entry
→ Initial SL/TP
→ Position Monitoring
→ Breakeven Adjustment
→ Trailing SL/TP
→ Exit
→ Reconciliation
→ Journal

==================================================

AUDIT AREAS

## 1. Current Lifecycle Implementation

Find:

- position monitoring services
- trade management services
- exit managers
- risk managers
- broker modification APIs
- stop-loss update logic
- take-profit update logic

Report:

FACT

FILE

CLASS

METHOD

CURRENT BEHAVIOR

==================================================

## 2. Auto Breakeven Audit

Verify whether auto breakeven exists.

If yes:

Verify:

- trigger condition
- profit threshold
- ATR/volatility adjustment
- exchange order modification
- reconciliation
- journal update
- restart recovery

If no:

State:

NOT IMPLEMENTED

==================================================

## 3. Trailing Stop / Trailing TP Audit

Verify:

- trailing logic existence
- activation condition
- distance calculation
- volatility adaptation
- long/short correctness
- exchange synchronization
- duplicate modification prevention

==================================================

## 4. Failure Analysis

Attempt to break lifecycle management:

Scenario:

- price moves quickly
- websocket disconnects
- broker rejects modification
- process restarts
- partial fill
- stale position data
- duplicate update request

For each:

Detection

Recovery

Residual Risk

==================================================

## 5. Production Impact Assessment

Classify each feature:

READY

PARTIALLY IMPLEMENTED

MISSING

RISK ACCEPTED

Explain impact on:

- Paper Trading
- Micro Capital
- Full Production

==================================================

## 6. Implementation Decision

Only if required:

Provide minimal implementation plan.

Constraints:

- Preserve architecture
- No redesign
- No unnecessary files
- Follow existing lifecycle

==================================================

FINAL OUTPUT

Provide:

1. Current capability
2. Missing functionality
3. Production risks
4. Required action before paper trading
5. Required action before real capital

Do not assume.

Do not claim implemented without code evidence.