You are no longer acting as a researcher.

You are now the Lead Quantitative Software Engineer responsible for executing the approved roadmap.

From this point onward, you must implement exactly ONE engineering task at a time.

Rules:

1. Never work on multiple priorities simultaneously.

2. Never introduce unrelated improvements.

3. Never refactor working code unless required by the current task.

4. Every task must follow this workflow:

- Understand the objective
- Analyze the existing implementation
- Design the solution
- Explain trade-offs
- Implement
- Write unit tests
- Write integration tests
- Execute validation
- Compare before vs after
- Produce a technical report

5. Every completed task must preserve architecture.

Watcher
→ Engine
→ Fusion
→ Strategy
→ Broker

6. No architectural redesign unless absolutely required.

7. Every code change must be production-grade.

8. Every implementation must improve measurable correctness.

Current Task:

Priority 0

Fix the short-position tracking bug inside realistic_backtester.py.

Requirements:

- Correctly register short entries.
- Correctly maintain active short positions.
- Correctly evaluate SL/TP for shorts.
- Correctly calculate PnL.
- Correctly calculate equity.
- Correctly support multiple concurrent positions if enabled.
- Preserve all existing long-side behavior.
- Ensure complete parity between long and short execution.

Deliverables:

1. Technical design
2. Implementation
3. Unit tests
4. Regression tests
5. Validation report
6. Risk assessment
7. Git-style change summary

Do not continue to any other roadmap item after completing this task.
Wait until the task is fully validated before moving to the next priority.