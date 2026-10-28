# TASK-0221 — C-33 reconnect observability

## Scope

Expose the transient exception already handled by the C-33-only supervisor without
changing the collector, candidate protocol, retry policy, or append-only ledger.

## Finding

C-33 remained fresh but eligible buckets stopped advancing at 511 while sessions
repeatedly ended and restarted. The supervisor intentionally retried the transient
failures but discarded their type and message, preventing causal diagnosis.

## Minimal correction

Every handled reconnect now writes one deterministic JSON diagnostic to stderr with
the attempt number, exception type, and message. The ledger remains unchanged and
incomplete or disconnected intervals remain ineligible.

## Acceptance

Focused tests verify both bounded backoff and the exact diagnostic record. A controlled
restart of only the authorized unauthenticated public collector is required to load the
launcher change and reveal the next transient failure cause.
