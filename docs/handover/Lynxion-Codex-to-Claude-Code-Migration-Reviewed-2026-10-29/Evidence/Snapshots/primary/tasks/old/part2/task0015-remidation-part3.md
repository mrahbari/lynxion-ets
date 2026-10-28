Act as the project's Technical Lead.

Stage 7 has been approved.

Before proceeding to Stage 8, perform a Final Operational Audit focusing on the remaining open questions.

IMPORTANT RULES

- Architecture is frozen.
- Do not redesign the system.
- Do not introduce unrelated refactoring.
- Base every conclusion on runtime evidence, logs, code paths, and collected metrics.
- If a change is required, it must be minimal and localized.

====================================================
Part 1 — Strategy Diversity Audit
====================================================

The previous report stated that only MTFTrend generated trades because market conditions did not satisfy the other strategies.

Do not assume this is correct.

Produce actual runtime statistics for every registered strategy.

For each strategy provide:

- Strategy name
- Enabled (Yes/No)
- Number of watcher observations received
- Number of Fusion signals received
- Number of strategy evaluations
- Number of signals generated
- Number of ExecutionIntent objects created
- Number of Risk Engine approvals
- Number of Broker submissions
- Number of executed VST orders
- Number of rejected orders
- Rejection reason breakdown

Present the results in a table.

If any strategy never executed, identify the exact reason.

If any strategy is disabled, explain where and why.

If any strategy is being starved by Fusion or RegimeEngine, identify the execution path.

====================================================
Part 2 — Position Sizing Audit
====================================================

Investigate the unexpectedly large SOL order (~$17,035).

Produce the complete sizing calculation.

Include:

- Wallet equity
- Available balance
- Configured risk percentage
- Risk amount
- Entry price
- Stop loss
- Stop distance
- ATR
- Volatility multiplier
- Confidence multiplier
- Correlation penalty
- Leverage
- Calculated quantity
- Calculated notional
- Final submitted quantity
- Final submitted notional

Show every intermediate calculation.

Determine whether the result is:

- Expected
- Bug
- Configuration issue

====================================================
Part 3 — Configurable Order Cap
====================================================

Design (do not implement yet) a minimal enhancement.

Requirement:

Add an OPTIONAL configuration value:

MAX_ORDER_NOTIONAL_USD

Behavior:

If unset:
Current behavior remains unchanged.

If configured:

final_notional = min(calculated_notional, configured_limit)

Requirements:

- No architectural changes.
- Risk calculations remain unchanged.
- The cap is applied immediately before broker submission.
- Risk Engine continues enforcing all existing limits.

Identify the exact class, method, and execution point where this cap should be applied.

====================================================
Part 4 — Startup Signal Replay Validation
====================================================

Verify whether the startup burst of MTFTrend orders is caused by historical buffer replay.

Trace the execution path:

Historical Candle Load
↓
Watcher
↓
Fusion
↓
MTFTrendStrategyAdapter
↓
generate_signal()
↓
ExecutionIntent

Determine:

- Is the strategy scanning the entire historical buffer?
- Is it generating signals from historical candles?
- Does it validate that the signal belongs to the latest candle?
- Is duplicate protection working?

If this is confirmed as a bug:

Propose the minimal fix that preserves the existing architecture.

====================================================
Deliverables
====================================================

Produce a report containing:

1. Executive Summary

2. Strategy Statistics Table

3. Position Sizing Audit

4. Startup Replay Analysis

5. Configurable Order Cap Design

6. Root Cause Analysis

7. Minimal Remediation Plan

8. Risk Assessment

9. Priority (Critical / High / Medium / Low)

Do not implement any changes yet.

Only investigate, collect evidence, and produce the technical report.