# TASK-0241 — Preregister C-35 compression-release continuation

## Scope and decision

Following TASK-0240's rejection of position-size and strategy-label aliases, admit one—not five—new
primary hypothesis. This preserves the sequential false-discovery policy while testing a mechanism
not defined by realized outcomes, sizing, or a production strategy label.

## Evidence boundary

`tasks/research/edge-candidate-register-v34.md` was committed before any C-35 prospective signal
or outcome. Its boundary is `2026-09-11T00:40:44Z` (`1789087244`). Only later public Binance USD-M
data may count; history is warmup only.

## Verdict

`KEEP — C-35 PREREGISTERED; OUTCOMES UNOPENED`.

Next, implement and test an append-only public collector/evaluator that enforces the frozen boundary
and remains structurally unable to place orders or use authentication.
