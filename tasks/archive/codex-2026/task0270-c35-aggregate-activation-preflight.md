# TASK-0270 — C-35 aggregate activation preflight

## Scope

Hash-bind the frozen aggregate protocol, math, evaluator, and unseal gate before any live outcome
or aggregate economics exists.

## Contract

- Freeze protocol and implementation SHA-256 values against commit `af04921`.
- Freeze 10,000 bootstrap samples, seed `350035`, 240 positions, 80 per side, and eight UTC weeks.
- Require the prepared commit to remain an ancestor of HEAD.
- Fail closed if economics were marked open or any code, protocol, or gate value drifts.

## Evidence

Six focused tests cover exact admission, threshold/seed/sample drift, and implementation tampering.
The real preflight passes while aggregate economics remain sealed.

## Verdict

`KEEP — AGGREGATE IMPLEMENTATION HASH-BOUND BEFORE FIRST OUTCOME`.
