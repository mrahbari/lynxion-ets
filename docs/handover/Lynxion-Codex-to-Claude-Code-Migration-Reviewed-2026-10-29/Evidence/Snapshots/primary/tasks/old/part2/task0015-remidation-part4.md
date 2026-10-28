The Operational Audit has now been completed and approved.

You are now authorized to implement the remediation phase.

IMPORTANT:
This project is under a strict Architecture Freeze policy.

The existing architecture, module boundaries, event flow, dependency graph, IoC, ports/adapters, messaging pipeline, Fusion engine, Strategy pipeline, Risk Engine, Broker layer, and execution lifecycle MUST remain unchanged.

You are NOT allowed to:
- redesign architecture
- refactor unrelated code
- move responsibilities between modules
- introduce new abstractions
- change public APIs
- rewrite existing subsystems
- add technical debt disguised as improvements

Only implement the smallest possible production-safe fixes required to resolve the issues confirmed by the audit.

---------------------------------------------------
Implementation Scope
---------------------------------------------------

Implement ONLY the following fixes.

──────────────────────────────
1. Strategy Freshness Validation
   ──────────────────────────────

Problem:
Historical setups generated during startup replay are incorrectly treated as fresh live signals.

Required implementation:

Every strategy adapter that consumes SetupEngine results must verify that the selected setup belongs to the latest candle in its data buffer.

If

setup.timestamp != latest_bar.timestamp

(or equivalent candle identity)

the adapter MUST return None.

Historical setups must never become ExecutionIntent.

Do not modify SetupEngine.

Do not modify DecisionPipeline.

Only validate freshness immediately before creating the Signal.

Apply consistently across every strategy adapter using the setup-scanning pattern.

──────────────────────────────
2. Stop Loss / Take Profit Ownership
   ──────────────────────────────

Architecture rule:

Strategy
↓

ExecutionIntent
↓

Risk Engine
↓

Broker

The Event System must never silently modify strategy risk parameters.

Current behavior:

Event System rewrites invalid SL/TP values.

Required behavior:

If SL or TP received from the Strategy is invalid:

- reject the order
- log a detailed warning
- write rejection to ExecutionTruthLedger
- do NOT modify SL
- do NOT generate fallback SL/TP
- do NOT silently continue

Broker layer must receive exactly the same SL/TP that were used by Risk Engine sizing.

Sizing SL == Execution SL

must always hold.

──────────────────────────────
3. Configurable Maximum Order Notional
   ──────────────────────────────

Introduce a configurable limit:

MAX_ORDER_NOTIONAL_USD

Requirements:

• Optional configuration
• Default:
disabled (current behavior unchanged)

If configured:

calculate

quantity × execution_price

If above limit:

scale quantity down

preserving

• direction
• leverage
• stop loss
• take profit

Log:

ORDER CAP ENGAGED

including

old quantity

new quantity

old notional

new notional

This is a safety cap only.

Risk Engine calculations remain unchanged.

──────────────────────────────
4. Heartbeat Timestamp Update
   ──────────────────────────────

Current issue:

Heartbeat timestamps update only after MarketObservation events.

During quiet markets the heartbeat appears stale although market data continues arriving.

Required fix:

Update heartbeat timestamps immediately after successful market data ingestion.

NOT

after pattern detection.

Do not change heartbeat thresholds.

Do not remove Heartbeat Guard.

Only update the timestamp source.

──────────────────────────────
5. Preserve Existing Safety Features
   ──────────────────────────────

Do NOT modify:

LiveExecutionGuard

ExecutionTruthLedger

Portfolio Risk Limits

Circuit Breaker

Kill Switch

Exposure Controls

Risk sizing formulas

Broker routing

Testnet detection

──────────────────────────────
6. Regression Protection
   ──────────────────────────────

After implementation execute all relevant tests.

Ensure:

existing tests continue passing

no regression introduced

all modified code passes linting

no new warnings

──────────────────────────────
Required Final Report
──────────────────────────────

After implementation provide a structured report including:

1.
Files modified

2.
Exact code locations

3.
Reason for each change

4.
Why architecture remains unchanged

5.
Evidence that

Sizing SL == Execution SL

after the fix

6.
Evidence that startup replay no longer generates historical orders

7.
Evidence that heartbeat timestamps continue updating during quiet markets

8.
Evidence that MAX_ORDER_NOTIONAL_USD correctly caps oversized orders

9.
Regression test summary

10.
Residual risks (if any)

Do not implement anything outside this approved scope.

If any additional issue is discovered, report it separately and do not fix it unless it is strictly required to complete one of the approved remediations.