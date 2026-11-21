# TASK-0225 — Investor demo state isolation

## Scope

Remove persistent runtime-state contamination from the existing deterministic paper
burst without changing production cooldown, risk, strategy, broker, or execution policy.

## Root cause

The burst used the real `SymbolCooldownGate` singleton, which loads both the repository
cooldown journal and recent losses from the production trade journal. It also constructed
incomplete order fixtures and a 200 USDT notional inconsistent with the 21 USDT VST hard
cap. Consequently all 87 demo decisions were blocked by unrelated runtime state.

## Minimal change

- Allow `SymbolCooldownGate` to receive task-local journal paths while retaining the
  existing defaults for every production caller.
- Allow `RiskEnforcement` and its VST factory to receive a task-local cooldown gate while
  preserving lazy use of the process singleton by default.
- Give the burst complete risk-admissible orders and use 20 USDT notional, below the
  frozen 21 USDT VST cap.
- Store all demo evidence in a unique temporary artifact directory.

## Evidence

- Two independent subprocess runs each routed all 87 decisions to `PAPER`.
- Each run created 174 valid hash-chained ledger records and reported
  `real_sends_to_exchange=0`.
- Stable summary fields were byte-equivalent across both runs; only latency, wall time,
  and unique artifact path were excluded.
- Focused suite: 49 passed.
- Full suite: 1,041 passed, one optional import-layering test skipped.

## Decision

`KEEP — P0-IR1 CLOSED`. Production default paths and behavior remain unchanged. This
proves an isolated paper execution-safety scenario; it does not prove strategy edge or
profitability.

## Next

TASK-0226: add a dedicated fail-closed investor-demo launcher that exposes only this
isolated scenario, prints an explicit environment/evidence banner, and rejects production
or broker-execution options.
