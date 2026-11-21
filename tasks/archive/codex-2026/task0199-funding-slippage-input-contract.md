# TASK-0199 — Funding and slippage input contract

## Scope

Implement disconnected funding-window and slippage admission for the preregistered
paired exit experiment. Do not read the active cohort or evaluate returns.

## Result

- Funding requires complete BingX perpetual coverage from entry through exit, explicit
  source, normalized symbol, unique settlements, UTC times, and finite rates.
- Only settlements strictly between entry and terminal exit are applied, with positive
  funding debited from LONG and credited to SHORT.
- The exact frozen 0.10% primary round-trip, 0.20% stress round-trip, and 0.10% candidate
  remaining-exit reserve are admitted; variants fail closed.
- Funding snapshots receive canonical SHA-256 provenance.

## Boundary

No funding endpoint, broker, runtime, cohort outcome, PnL, or policy setting was opened.

## Next

TASK-0200 specifies and implements the paired per-position outcome calculation, while
keeping aggregate results unopened until every minimum coverage gate is met.
