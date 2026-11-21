# TASK-0247 — C-35 candle-ledger verifier

## Scope

Add a deterministic gate between the append-only public candle ledger and any future signal-state
evaluation.

## Verification contract

Fail closed on unknown symbols, malformed timing, duplicates, gaps, incorrect boundary roles,
invalid source hashes, non-finite/negative values, invalid OHLC ordering, or an incomplete frozen
universe. No missing interval is interpreted as a zero or forwarded candle.

## Evidence

- Four focused regressions pass for a complete panel and rejection of duplicate, gap, and boundary
  drift.
- The activated ledger passes with 17,514 rows, 2,919 per symbol, 17,388 warmup and 126 prospective
  rows, and zero integrity defects.
- No signal or outcome was evaluated.

## Verdict

`KEEP — CANDLE EVIDENCE PASSES FAIL-CLOSED INTEGRITY; SIGNAL STATE STILL UNOPENED`.
