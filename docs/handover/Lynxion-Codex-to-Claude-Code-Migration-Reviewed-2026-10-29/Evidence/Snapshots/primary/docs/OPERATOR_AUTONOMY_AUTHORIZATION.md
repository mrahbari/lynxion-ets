# Operator Autonomy Authorization

> **2026-10-28 applicability note:** ordinary in-scope engineering remains authorized without routine reapproval. Read this older general grant together with later explicit limits and the current unresolved recovery gate. It does not permit clearing UNKNOWN, broker writes, account/credential reset or startup while recovery is blocked. [Exact current boundary](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/docs/LYNXION_CURRENT_STATUS_AND_BLOCKERS.md).

**Recorded:** 2026-08-29
**Scope:** Lynxion ETS repository and VST/paper engineering workflow

The operator explicitly authorizes autonomous continuation without confirmation for routine,
reversible, in-scope work, including:

- diagnosis, research, attribution, backtesting, walk-forward/OOS validation, and reporting;
- minimal code fixes required by verified defects;
- unit, integration, regression, smoke, and read-only operational checks;
- Git staging and commits for completed, verified tasks;
- creation and maintenance of task reports, progress ledgers, and research artifacts;
- controlled VST/paper runtime reloads or restarts when required to load verified changes,
  provided existing protective-position invariants are checked before and after the operation;
- automatic progression to the next roadmap task after each completion gate.

This authorization does not override safety or platform approval boundaries. Separate explicit
approval remains required where real funds, production secrets, destructive database/file
operations, data loss, security-boundary changes, paid external services, legal/compliance
decisions, or irreversible architectural choices may be affected.

The task boundary, minimal-change rule, profitability-first priority, and all trading validation
standards in `AGENTS.md` remain mandatory.
