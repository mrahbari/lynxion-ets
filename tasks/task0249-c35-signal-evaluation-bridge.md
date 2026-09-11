# TASK-0249 — C-35 signal-evaluation bridge

## Scope

Connect the verified public candle ledger to the pure C-35 evaluator without opening an outcome or
automatically writing a signal.

## Contract

- Refuses evaluation unless the full candle ledger passes TASK-0247 integrity.
- Evaluates only exact hourly decisions whose just-closed post-boundary candle exists for all six
  symbols.
- Preserves chronological order and returns only the first qualifying portfolio signal.
- Hashes the complete causal input panel used for the ranked decision.
- Defaults to read-only dry-run; append requires the explicit `--commit-signal` flag and then passes
  through TASK-0248's append-only state gate.

## Evidence

Three focused regressions verify common-time intersection, deterministic input hashing, and earliest
signal selection. No live evaluation was run and no signal/outcome ledger was created.

## Verdict

`KEEP — VERIFIED CANDLE-TO-SIGNAL BRIDGE READY; CONTROLLED FIRST EVALUATION NEXT`.
