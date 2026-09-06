# TASK-0168 — C-33 Live Warmup Snapshot

**Status:** COMPLETE — COLLECTING

Materialized the first reproducible C-33 warmup artifact from one exact active-ledger snapshot. The
artifact is bound to source SHA-256
`c72b3e2207e6873c66ae5084baea432d84ed3c9211a5e48cee69c2bc35ac06bb` and retains the frozen
activation boundary `1788694535`.

## Snapshot evidence

- 25 eligible completed five-minute buckets; 150 bucket-symbol rows across all six frozen symbols.
- 170 eligible observed liquidation snapshots in 54 non-zero bucket-symbol rows.
- 901,832.46278 USDT eligible observed snapshot notional.
- Source snapshot: 134 heartbeats, 792 closed klines, 175 liquidation records, one active session.
- First eligible bucket: `1788694800000`; last eligible bucket: `1788702000000`.

The difference between 175 stored and 170 eligible liquidation snapshots is preserved: events in
partial/ineligible buckets are not converted to zero or imported into warmup rows. No signal,
threshold, virtual trade, funding, or outcome was calculated. The verdict remains `COLLECTING`.

## Verification

- The TASK-0167 materializer's six focused auditor/materializer tests pass.
- The artifact contains exactly `25 * 6 = 150` rows and its embedded source digest is non-empty.

## Next unit

TASK-0169 should add a deterministic snapshot-verification command so committed materializations can
be checked for schema, row uniqueness, bucket completeness, frozen universe, and aggregate totals
without reopening live source data or evaluating the signal.
