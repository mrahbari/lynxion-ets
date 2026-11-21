# TASK-0248 — C-35 signal-state append contract

## Scope

Create the append-only state boundary for future C-35 virtual signals without evaluating or
recording any current signal or outcome.

## Contract

- Accept only the frozen C-35 universe, LONG/SHORT sides, strict post-boundary hourly decision bar,
  next-open entry, and exact eight-bar exit schedule.
- Bind each signal to a 64-character causal-input SHA-256.
- Deduplicate by symbol/decision time and reject a second portfolio signal while one is unresolved.
- Validate existing SIGNAL/OUTCOME ordering and fail on duplicate, orphan, malformed, or unknown
  events. Writes are append-only and fsynced.
- The module contains no broker, authentication, order, account, or production integration.

## Evidence

Four regressions pass for idempotent append, unresolved-position rejection, post-outcome admission,
and strict-boundary rejection. The live signal ledger remains absent; no outcome was opened.

## Verdict

`KEEP — APPEND-ONLY SIGNAL STATE READY; FIRST SIGNAL STILL UNOPENED`.
