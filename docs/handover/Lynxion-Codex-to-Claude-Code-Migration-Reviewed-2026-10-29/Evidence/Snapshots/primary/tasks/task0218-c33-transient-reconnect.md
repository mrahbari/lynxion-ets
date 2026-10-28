# TASK-0218 — C-33 transient reconnect

## Status

`COMPLETE — RECONNECT SUPERVISOR VERIFIED BY TASK-0219`

## Incident

The resumed public collector ended after reaching 443 eligible buckets because Binance's
WebSocket peer reset the TCP connection without a close frame. The append-only collector
correctly wrote `ENDED`, leaving zero active sessions and no ledger corruption, but the
one-shot launcher did not reconnect.

## Minimal correction

The dedicated resume launcher now supervises the unchanged pinned collector and retries
only transient `OSError`/timeout failures. Each attempt remains an explicit independent
session, so gaps are excluded by the existing auditor. Backoff is 1, 2, 4, 8, 16, 32,
then at most 60 seconds. The original collector blob and candidate protocol remain
unchanged.

## Acceptance

Synthetic tests prove retry and delay capping. No historical data is imported, existing
records are not rewritten, and no trading runtime, broker, order, account, strategy, or
risk setting is accessed.
