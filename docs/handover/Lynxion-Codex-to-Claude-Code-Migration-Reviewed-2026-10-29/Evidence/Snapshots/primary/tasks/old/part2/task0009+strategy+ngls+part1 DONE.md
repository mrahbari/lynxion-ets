Implementation Sprint 1

Research is complete.

The architecture is frozen.

From this point forward, do not perform any new research, redesign, or speculative engineering.

Your task is to integrate the validated v2 architecture into the existing Lynxion-ETS production codebase incrementally.

Mission

Replace the legacy trading decision pipeline with the new multi-timeframe pipeline while keeping the system operational at every step.

Implementation principles

- Keep changes as small as possible.
- Reuse existing code whenever possible.
- Do not create unnecessary files.
- Do not redesign the architecture.
- Do not introduce new abstractions unless absolutely required.
- Maintain backward compatibility until the migration is complete.
- Each implementation must compile and pass the full test suite.

Migration Order

Phase 1
Implement the 4H Macro Regime Engine by refactoring the existing regime-related watchers and logic.

Acceptance Criteria:
- Existing behaviour preserved where applicable.
- Regime state is produced from the new engine.
- No strategy logic changed.

Phase 2
Implement the 1H Market Structure Engine.

Acceptance Criteria:
- Swing structure
- Support/Resistance
- Volume Profile
- Directional bias

No trade execution changes.

Phase 3
Replace setup generation with the new 15m Setup Engine.

Acceptance Criteria:
- Existing strategies remain functional.
- New setup engine produces independent setup objects.
- No execution changes.

Phase 4
Replace the execution confirmation layer with the 5m Execution Engine.

Acceptance Criteria:
- OBI
- CVD
- Flow confirmation

No broker changes.

Phase 5
Integrate the 1m Execution Optimizer.

Acceptance Criteria:
- Maker-first execution
- Queue priority
- Spread validation
- Optional component

Broker remains BingX only.

Rules

Before every implementation answer:

1. What production problem is being solved?
2. Why is the current implementation insufficient?
3. Why is this the smallest correct production change?
4. Which existing code is being reused?

Before modifying any file:

- Search for an existing implementation.
- Extend existing modules whenever reasonable.
- Only create a new file if there is no appropriate existing location.

After each phase:

Provide only a concise implementation summary in chat.

Do not generate reports.

Do not generate markdown documents.

Do not generate architecture documents.

Do not continue automatically to the next phase.

Stop after completing exactly one migration phase.

Wait for my review before proceeding.