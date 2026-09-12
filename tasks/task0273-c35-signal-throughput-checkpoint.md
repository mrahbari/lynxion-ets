# TASK-0273 — C-35 signal-throughput checkpoint

## Scope

Measure collection feasibility from verified decision and signal counts without opening outcomes,
changing thresholds, or treating signal frequency as edge.

## Contract

- Verify candle integrity, decision-to-candle hashes, and signal ledger integrity first.
- Use completed hourly decision count rather than wall-clock duration.
- Report signal rate and a mechanical 240-outcome projection only after at least one signal.
- Freeze the first interpretive checkpoint at 168 valid decisions (one decision-week).
- Keep economics sealed and verdict `COLLECTING`; this cannot reject or promote C-35.

## Evidence

Three tests cover zero-signal honesty, decision-based projection, and the 168-decision checkpoint.
The live cohort has 35 valid decisions, zero signals, and therefore no defensible duration estimate.

## Verdict

`KEEP — THROUGHPUT MONITOR ACTIVE; FIRST INTERPRETATION AT 168 DECISIONS`.
