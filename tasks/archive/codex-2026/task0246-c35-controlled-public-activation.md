# TASK-0246 — C-35 controlled public activation

## Scope

Run the commit-bound C-35 collector for the first time after a passing TASK-0245 integrity check.
Collect candles only; do not evaluate signals or open outcomes.

## Execution evidence

- Preflight passed against activation commit `0e22d1706b249944035fed2892f4a635aed49d73`.
- The first network attempt reset after partially appending valid pages. The idempotent retry
  resumed without deletion or duplicate evidence and completed all six frozen symbols.
- Ledger: 17,514 rows; exactly 2,919 per symbol; zero timestamp gaps, zero duplicate keys, and zero
  warmup/prospective role errors.
- 17,388 rows are `WARMUP_ONLY`; 126 post-boundary rows are `PROSPECTIVE`.
- Ledger SHA-256: `84412dec9d5cf61bbad5bb0e81bc1fc37a6f43f6446021be5b50dc64056955ba`.

## Boundary

Only the public unauthenticated Binance USD-M kline endpoint was called. No signal evaluator,
aggregate outcome, broker adapter, account, key, order, production runtime, or trading setting was
used or changed.

## Verdict

`COLLECTING_CANDLES_ONLY — COMPLETE CONTIGUOUS INITIAL PANEL; SIGNALS UNOPENED`.

Next, add a deterministic ledger verifier and signal-state append contract before evaluating the
first eligible decision.
