# TASK-0326 — Remove superseded misleading documents

## Scope

Remove only documentation already identified as superseded and materially likely to mislead an AI
or technical reviewer. Preserve audit records, decision history, current roadmaps, frozen research
protocols, source, tests, runtime, configuration, and evidence data.

## Removed

- `tasks/comprehensive_strategy_and_platform_roadmap.md`
- `tasks/comprehensive_strategy_logic_audit_and_long_term_roadmap.md`
- `docs/LYNXION_PROJECT_CONTEXT.md`
- `docs/LYNXION_PROJECT_CONTEXT-OLd.md`

The deleted files contained stale Alpha/edge labels, schedules, runtime counts, exchange-state
assertions, or strategy recommendations that conflict with the current evidence hierarchy. The
three tracked files remain recoverable from Git history; the untracked `-OLd` duplicate was removed
under explicit operator authorization.

## Preserved

- `docs/AI_START_HERE.md` — current AI handoff
- `docs/ROADMAP_INDEX.md` — current roadmap navigation
- `tasks/00-right-path.md` — governing mission
- `docs/LYNXION_PROGRESS_LEDGER.md` — execution history
- investor evidence, dated gap assessment, task records, and frozen candidate preregistrations

## Verdict

`KEEP — FOUR SUPERSEDED DOCUMENTS REMOVED; NO SOURCE, POLICY, DATA, OR EVIDENCE CHANGE`.
