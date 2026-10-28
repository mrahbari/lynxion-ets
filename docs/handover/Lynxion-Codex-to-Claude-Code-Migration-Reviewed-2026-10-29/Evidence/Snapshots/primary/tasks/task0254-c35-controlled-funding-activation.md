# TASK-0254 — C-35 controlled funding activation

## Scope

Run the first commit-bound public funding query, verify records and query coverage, and preserve an
activation receipt. Do not evaluate or open an outcome.

## Evidence

- TASK-0253 real preflight passed against commit `b51738daa74a70909c22cde71018e0a7b480cd03`.
- Six successful public coverage receipts and 12 funding settlements were appended, exactly two per
  frozen symbol, strictly after the prospective boundary.
- Each settlement binds uniquely to a same-symbol request range and raw-response SHA-256.
- Four verifier tests pass for complete evidence plus missing, duplicate, and unbound rejection.
- Funding SHA-256: `82f9003a091256d7091072488ee1dd4ed7ad25bf23a67e1106aa1eb230558194`.
- Coverage SHA-256: `c794c61ef281f54aacc3f0fb6ffd61bdd8e70d450186661e6ec6f920e3819a3b`.

## Boundary

Only the unauthenticated public Binance USD-M funding endpoint was queried. No signal, outcome,
broker, order, account, runtime, leverage, sizing, or production setting was used or changed.

## Verdict

`KEEP — PUBLIC FUNDING ACTIVE AND VERIFIED; OUTCOMES REMAIN UNOPENED`.
