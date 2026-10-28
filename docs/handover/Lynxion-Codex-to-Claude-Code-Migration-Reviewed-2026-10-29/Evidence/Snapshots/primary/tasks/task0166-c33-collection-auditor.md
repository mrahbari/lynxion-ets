# TASK-0166 — C-33 Collection Auditor

**Status:** COMPLETE

Added a deterministic, read-only auditor for the active prospective C-33 cohort. It validates the
frozen activation manifest, strict post-activation timestamps, record uniqueness, raw-message hashes,
session lifecycle, universe, and exact five-minute bucket eligibility. A bucket is eligible only under
one uninterrupted session with one successful heartbeat and all six closed candles in every minute.

The auditor aggregates observed liquidation count/notional only for eligible completed buckets. It
does not calculate thresholds, signals, trades, or outcomes and does not alter the active collector.

## Acceptance evidence

- Focused auditor tests cover a complete bucket, missing heartbeat, duplicate/raw corruption, and
  pre-activation rejection.
- Live audit remains `COLLECTING`; no frozen gate is opened or evaluated.

## Next unit

TASK-0167 should keep monitoring the cohort and specify the forward-only warmup materializer without
opening outcomes or changing the frozen C-33 contract.
