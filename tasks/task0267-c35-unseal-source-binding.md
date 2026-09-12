# TASK-0267 — C-35 unseal-to-source binding

## Scope

Require the live aggregate-unseal command to recompute completed outcomes from verified source
ledgers before any sample can count toward opening aggregate evaluation.

## Contract

- Load candle, funding, coverage, and signal/outcome ledgers together.
- Pass full event integrity and exact source recomputation before counting minimum gates.
- Reject finite, well-shaped, hash-looking outcomes when their economics differ from source data.
- Keep the live result sealed and preserve all frozen strategy rules.

## Evidence

Ten focused integrity/unseal tests pass, including finite economic tampering. The current empty
signal ledger passes source binding and remains sealed.

## Verdict

`KEEP — UNSEAL COMMAND NOW REQUIRES EXACT SOURCE-BOUND OUTCOMES`.
