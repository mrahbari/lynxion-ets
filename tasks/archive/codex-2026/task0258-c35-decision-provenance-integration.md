# TASK-0258 — C-35 decision provenance integration

## Scope

Connect TASK-0257's append-only decision evidence to the verified candle-to-signal bridge without
running it on live data in this unit.

## Behavior

- Skip every already-recorded exact-hour decision.
- Evaluate new decisions chronologically, hash each complete causal input panel, and append
  NO_SIGNAL evidence only with explicit `--commit-decisions` or `--commit-signal`.
- Stop at the first signal. A SIGNAL decision is written only after its append-only signal record
  succeeds, preventing a decision-only partial state from losing the signal on retry.
- Preserve read-only default and existing explicit signal opt-in.

## Evidence

Five bridge regressions pass, including recorded-history skipping and first-signal stopping. No live
decision, signal, or outcome is opened here.

## Verdict

`KEEP — DECISION PROVENANCE INTEGRATED; CONTROLLED STATE ACTIVATION NEXT`.
