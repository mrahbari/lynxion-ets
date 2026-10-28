# TASK-0262 — C-35 signal-ledger integrity gate

## Scope

Fail closed before outcome orchestration if prospective signal or outcome identity, timing, hashes,
or numeric evidence has been malformed or tampered with.

## Contract

- Validate frozen candidate, universe, side, signal key, exact hourly schedule, boundary, horizon,
  and input SHA-256 for every signal.
- Require outcomes to follow a unique signal and preserve candidate, symbol, side, entry, and exit.
- Reject incomplete, non-finite, non-positive-fill, duplicate, orphan, or unproven outcomes.
- Run the gate before attempting any live resolution; do not compute aggregate economics.

## Evidence

Four focused tests cover valid/empty state, timing and provenance tampering, identity mismatch,
non-finite economics, and missing evidence hash. The live ledger remains empty and passes.

## Verdict

`KEEP — SIGNAL/OUTCOME LEDGER INTEGRITY ENFORCED BEFORE RESOLUTION`.
