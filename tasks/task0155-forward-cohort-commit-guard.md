# TASK-0155 — Forward Cohort Commit Guard

**Status:** PRE-REGISTERED — REPOSITORY IMPLEMENTATION PENDING

## Objective

Prevent a restarted runner from silently loading a different code revision while continuing to
write events under an activation manifest that freezes an older commit.

## Confirmed Defect

The tracked `lynxion` wrapper reuses `commit` from an existing activation manifest without comparing
it to `git rev-parse HEAD`. After TASK-0154, HEAD differs from the active TASK-0151 manifest. A
direct restart would therefore label new-code events with the old commit and contaminate provenance.

## Minimal Repository Scope

1. Resolve HEAD and the existing manifest commit before starting Python.
2. If they differ, abort before runner startup with a clear non-secret message; never rewrite the
   manifest or append new-code events to the old cohort.
3. Preserve the existing same-commit continuation behavior.
4. Support a new cohort only through an explicit, empty root supplied at an operator-approved
   deployment. Freeze a new run ID, UTC boundary, and actual HEAD before its first event.
5. Keep the legacy TASK-0151 cohort immutable and auditable at its existing path.

## Acceptance Criteria

- Disconnected tests cover same-commit continuation, commit mismatch refusal, malformed manifest,
  non-empty/conflicting new root, and new empty-root activation metadata.
- Mismatch and malformed state fail before `run_trading_system.py` can execute.
- No runner reload, broker call, order, policy change, data deletion, or historical import occurs.

## Deployment Boundary

Repository hardening is authorized as ordinary fail-closed engineering. Starting the TASK-0154
code under a new cohort remains a separate runtime approval gate.
