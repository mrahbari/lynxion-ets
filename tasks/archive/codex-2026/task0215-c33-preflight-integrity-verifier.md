# TASK-0215 — C-33 preflight integrity verifier

## Status

`COMPLETE — FAIL-CLOSED PREFLIGHT READY; RUNTIME STILL PROHIBITED`

## Objective

Make the TASK-0214 baseline executable as a pre-start integrity gate. This task must not
start the collector, access the network, or modify either C-33 artifact.

## Contract

The verifier requires byte-exact manifest and ledger SHA-256 matches, reruns the full
C-33 audit, compares every frozen lifecycle/counter/watermark field, and requires zero
active sessions. Any artifact or audit drift fails closed.

`PREFLIGHT_VERIFIED` means only that the original 351-bucket ledger is still untouched
and suitable for the separately gated TASK-0209 resume sequence. It is not runtime
authorization, collection liveness, or an edge verdict.

## Acceptance

Synthetic tests cover the unchanged baseline, manifest mutation, ledger mutation, audit
metadata drift, and an already-active session. The real frozen baseline also verifies.
No runtime, network, broker, order, backfill, or candidate outcome was accessed.
