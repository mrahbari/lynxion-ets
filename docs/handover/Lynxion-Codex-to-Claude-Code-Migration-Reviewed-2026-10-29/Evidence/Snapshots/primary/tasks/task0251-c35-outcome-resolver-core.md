# TASK-0251 — C-35 outcome resolver core

## Scope

Implement deterministic two-hour virtual outcome resolution and append-only terminal state without
opening any live signal or aggregate result.

## Contract

- Requires the exact entry-through-exit sequence of nine contiguous 15-minute open timestamps.
- Uses next-open entry and the open eight bars later; no close or intra-candle substitution.
- Applies public funding settlements strictly after entry and at/before exit, with LONG-pay/
  SHORT-receive signs, and fails closed when funding coverage is incomplete.
- Reports frozen 0.20%, primary 0.30%, and stress 0.50% friction without leverage or sizing.
- Binds the used candle/funding evidence with SHA-256 and appends an OUTCOME only after its SIGNAL;
  orphan and duplicate outcomes fail closed or deduplicate.

## Evidence

Four focused tests cover LONG/SHORT economics, strict funding boundary/sign, candle/funding
incompleteness, and append-only terminal ordering/idempotency.

## Verdict

`KEEP — FUNDING/COST-AWARE OUTCOME CORE READY; NO LIVE SIGNAL OR OUTCOME OPENED`.

Next, add the public funding collector and its coverage proof before activating terminal resolution.
