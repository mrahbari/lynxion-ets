# TASK-0169 — C-33 Snapshot Verifier

**Status:** COMPLETE — COLLECTING

Added a deterministic verifier for committed C-33 warmup artifacts. It validates exact schemas,
identity, frozen `COLLECTING` verdict, source digest format, source-count integrity, exact six-symbol
coverage per bucket, UTC five-minute boundaries, row uniqueness/canonical order, and count/notional
consistency without opening the live source ledger.

The verifier reports only collection totals. It does not calculate dominance, percentiles, signals,
trades, funding, or outcomes.

## Acceptance evidence

- The committed TASK-0168 artifact verifies at 25 buckets, 150 rows, 170 eligible observed snapshots,
  and 901,832.46278 USDT observed notional.
- Mutation tests fail closed for row-count, universe, boundary, zero/notional, and digest violations.
- Full suite: 928 passed, one optional import-linter check skipped.

## Next unit

TASK-0170 should define a sparse checkpoint cadence for C-33 so evidence snapshots are created only
at material collection milestones, avoiding repeated audit-only work while prospective warmup runs.
