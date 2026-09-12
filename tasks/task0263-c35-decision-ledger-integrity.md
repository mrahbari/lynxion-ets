# TASK-0263 — C-35 decision-ledger integrity

## Scope

Make the existing decision-ledger reader fail closed on provenance, verdict, payload, and schedule
tampering before old records can suppress a prospective hourly evaluation.

## Contract

- Validate exact-hour post-boundary decision times and SHA-256 input provenance on read.
- Require `NO_SIGNAL` to have no selected payload.
- Require `SIGNAL` to contain exactly the frozen selected fields, universe, side, finite metrics,
  entry time, and two-hour exit schedule.
- Preserve append-only/idempotent behavior and all frozen strategy rules.

## Evidence

Six focused decision-ledger tests pass, including tampered hash, inconsistent verdict payload, and
selected-signal schedule rejection. The live 25-decision ledger passes unchanged.

## Verdict

`KEEP — DECISION LEDGER NOW FAILS CLOSED ON TAMPERING`.
