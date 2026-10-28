# Lynxion ETS – SEV-1 Critical Incident: Unauthorized Order Placement & Missing Stop-Loss Elimination

Role:
Principal Software Architect, Principal Quant Engineer, Senior Trading Systems Auditor, Production Reliability Engineer.

Priority:
SEV-1 (Highest Possible)

Status:
ROOT CAUSE INVESTIGATION & PERMANENT FIX REQUIRED
DO NOT IMPLEMENT QUICK PATCHES.
DO NOT ASSUME ANY PREVIOUS FIX IS CORRECT.
ZERO TRUST AUDIT.

==================================================
BACKGROUND
==================================================

A critical production issue still exists despite multiple previous reports claiming it was fixed.

Observed production behavior:

- Orders are still being created without Telegram notifications.
- Orders are still being created without Stop Loss.
- Multiple consecutive orders (XMR incident) were opened outside the expected workflow.
- Some trades effectively carried 100% downside risk.
- Previous AI reports incorrectly concluded the issue was resolved.

Therefore ALL previous assumptions must be discarded.

Treat the current system as potentially unsafe until proven otherwise.

==================================================
MISSION
==================================================

Perform a complete architecture-wide forensic investigation.

Your objective is NOT to fix one bug.

Your objective is to prove that unauthorized order creation is impossible anywhere in the codebase.

==================================================
AUDIT REQUIREMENTS
==================================================

Trace EVERY execution path capable of creating, modifying or submitting an order.

Search for:

- place_order
- submit_order
- create_order
- send_order
- broker.execute
- broker.place*
- adapter methods
- REST API calls
- websocket execution
- async execution
- retry logic
- emergency execution
- recovery logic
- background jobs
- scheduled tasks
- event listeners

For every path produce:

- caller
- call stack
- entry point
- authorization source
- risk validation
- stop loss validation
- notification trigger
- final broker call

==================================================
GLOBAL ORDER GATE
==================================================

Verify whether a SINGLE authoritative order gate exists.

If not,
identify every bypass.

The architecture must guarantee:

NO ORDER
CAN REACH
ANY BROKER

unless ALL of these are true:

✓ Strategy approved
✓ Fusion approved
✓ ExecutionIntent exists
✓ Risk Manager approved
✓ Position sizing completed
✓ Stop Loss valid
✓ Take Profit valid
✓ Exposure validated
✓ Notification prepared
✓ Audit logging completed

If ANY route bypasses this sequence,
report it as SEV-1.

==================================================
STOP LOSS ENFORCEMENT
==================================================

Prove that every order satisfies:

- Stop Loss exists
- Stop Loss is finite
- Stop Loss is on the correct side
- Risk percentage <= configured maximum
- Stop Loss distance > minimum
- Stop Loss distance < maximum

Reject ANY order violating these rules.

No fallback.

No warning.

Hard reject.

==================================================
DELIVERABLE
==================================================

Return:

1. Complete call graph
2. Root cause(s)
3. Every bypass
4. Architecture violations
5. Required fixes
6. Validation plan
7. Regression tests
8. Why previous fixes failed
9. Proof that the issue cannot reappear

Do NOT stop until you can mathematically justify that unauthorized order placement is impossible.