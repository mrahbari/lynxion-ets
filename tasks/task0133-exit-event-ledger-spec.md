# TASK-0133 — Exit Event Ledger Specification

**Status:** COMPLETE — OBSERVABILITY CONTRACT FROZEN

## Objective

Define the minimum forward-only evidence needed to evaluate profit giveback without retrospective
inference or changes to live exit behavior.

## Result

- Frozen an append-only, secret-free event contract linking manager evaluations, stop requests,
  broker responses, exchange visibility, state commits, restart hydration, and exit fills.
- Unknown leverage must remain null; the current 10x default cannot enter evidence as authoritative.
- A future exit-policy candidate requires a separately committed prospective boundary and data gate.
- No production code, order, risk, trailing, leverage, or symbol-admission behavior changed.

Evidence: `docs/LYNXION_EXIT_EVENT_LEDGER_SPEC.md`.
