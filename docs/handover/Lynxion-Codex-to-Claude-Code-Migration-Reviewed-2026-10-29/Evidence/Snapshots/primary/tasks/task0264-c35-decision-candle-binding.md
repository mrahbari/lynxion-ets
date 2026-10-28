# TASK-0264 — C-35 decision-to-candle binding

## Scope

Recompute every recorded decision's causal candle-input hash before it can suppress an hourly
evaluation.

## Contract

- Require every recorded decision time to remain supported by complete frozen-universe inputs.
- Recompute the existing canonical causal-panel SHA-256 and compare it with the recorded hash.
- Fail closed before evaluating or appending any later decision when inputs disappeared or drifted.
- Preserve all frozen C-35 signal rules and append-only ledgers.

## Evidence

Focused tests cover exact binding, hash drift, and missing-input rejection. The complete live
decision ledger binds to the current verified candle ledger.

## Verdict

`KEEP — RECORDED DECISIONS ARE CRYPTOGRAPHICALLY BOUND TO CAUSAL CANDLES`.
