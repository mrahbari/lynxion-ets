# TASK-0170 — C-33 Sparse Checkpoint Cadence

**Status:** COMPLETE — COLLECTING

Defined immutable collection checkpoints at 25, 100, 500, 1,000, 2,000, 4,000, 8,000, and 8,640
eligible five-minute buckets. The checker verifies the previous committed artifact, reads one exact
live snapshot through the frozen materializer, and reports whether a milestone was crossed. It does
not write an artifact, calculate a signal, or evaluate an outcome.

The first 25-bucket snapshot already exists. Until 100 eligible buckets, C-33 requires liveness/error
monitoring only; routine heartbeat snapshots are prohibited. This keeps the engineering loop focused
on independent edge research while the forward-only 30-day warmup matures.

## Acceptance evidence

- Tests cover no-op checks, delayed checks crossing multiple milestones, the final 8,640 boundary,
  and fail-closed count regression/type validation.
- Nineteen focused tests pass; the full suite passes 935 tests with one optional import-linter skip.
- The current live check found 38 eligible buckets and remains `COLLECTING`; the next checkpoint is 100.

## Next unit

TASK-0171 must leave C-33 collecting and select the next genuinely independent profitability
hypothesis from unused causal data/mechanisms. It may not reslice or tune rejected candidates.
