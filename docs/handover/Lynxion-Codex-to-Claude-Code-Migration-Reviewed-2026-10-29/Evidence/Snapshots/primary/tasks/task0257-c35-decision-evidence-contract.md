# TASK-0257 — C-35 decision evidence contract

## Problem

The evaluator reported cumulative valid-decision counts but did not preserve a hash-bound record for
each `NO_SIGNAL` decision. Re-evaluation remained deterministic, yet an independent reviewer could
not prove which causal input produced each negative decision.

## Minimal addition

- Append one fsynced DECISION event per exact post-boundary hour, including causal-input SHA-256.
- Record only `NO_SIGNAL` or the frozen selected-signal fields; never outcome or aggregate metrics.
- Deduplicate decision time and fail closed on malformed history, identity, boundary, timing, hash,
  universe, or selected-signal mismatch.
- No broker, account, order, runtime, production, or strategy dependency.

## Evidence

Four tests pass for no-signal evidence, selected-field restriction, idempotency, and mismatch/
boundary rejection. The live decision ledger remains absent pending bridge integration.

## Verdict

`KEEP — APPEND-ONLY DECISION PROVENANCE READY; INTEGRATION NEXT`.
