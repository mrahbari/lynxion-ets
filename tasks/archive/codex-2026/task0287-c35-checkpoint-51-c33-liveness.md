# TASK-0287 — C-35 checkpoint 51 and C-33 liveness

## Scope

Run the frozen C-35 public-only pipeline and check C-33 against its latest verified 504-bucket
snapshot. Preserve all gates; do not authenticate, access a broker account, or trade.

## Evidence

- C-35: all eleven stages pass; 18,606 candles, 1,218 prospective records, 51 decisions, zero gaps,
  duplicates, boundary errors, signals, or outcomes. Aggregate economics remain sealed.
- C-33: exactly one active session and 740 eligible completed buckets. No checkpoint is due when
  compared with the verified 504-bucket snapshot; the next frozen milestone is 1,000.
- Using the obsolete 25-bucket snapshot would falsely re-report crossed checkpoints; the current
  check now defaults to `warmup_snapshot_task0220.json`. A focused regression binds that default.

## Verdict

`KEEP — C-33 STALE CHECKPOINT DEFAULT FIXED; NO EDGE EVIDENCE OR GATE TRANSITION`.
