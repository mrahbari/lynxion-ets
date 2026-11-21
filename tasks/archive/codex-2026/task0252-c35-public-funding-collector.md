# TASK-0252 — C-35 public funding collector

## Scope

Implement the public funding evidence needed by TASK-0251 without activating terminal resolution.

## Contract

- Fixed unauthenticated Binance USD-M funding-history endpoint and frozen six-symbol universe.
- Appends exact decimal rates with response SHA-256 and deduplicates symbol/settlement timestamp.
- Separately appends successful query-coverage receipts, including valid empty responses, so absence
  of a settlement is distinguishable from missing data.
- Fails closed on malformed, unordered, out-of-request, or unrecognized evidence.
- Contains no API key, broker, account, order, strategy runtime, or production dependency.

## Evidence

Four focused regressions cover populated and empty coverage, idempotent append, and request-boundary
rejection. No network call, signal, or outcome occurred in this task.

## Verdict

`KEEP — PUBLIC FUNDING/COVERAGE COLLECTOR READY; CONTROLLED ACTIVATION NEXT`.
