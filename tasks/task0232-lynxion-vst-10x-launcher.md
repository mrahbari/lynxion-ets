# TASK-0232 — Lynxion VST 10x launcher

## Scope

After explicit operator authorization, set the tracked `./lynxion` VST runner to request and
authoritatively verify 10x isolated leverage for new entries. Do not change the hard 21 USDT
per-order cap, 1,000 USDT portfolio cap, existing positions, or real-money configuration.

## Decision

The override is scoped to the official launcher rather than `.env` or global loader defaults.
Both `RISK_MAX_LEVERAGE` and `MAX_LEVERAGE` are pinned to 10; changing only one would trigger the
existing conflicting-ceilings rejection. Existing positions retain their exchange leverage.

## Behavioral impact

- New accepted entries request 10x and must pass isolated-margin/leverage exchange readback.
- Notional exposure limits remain unchanged.
- Required margin is lower for the same capped notional.
- ROE-based 6% breakeven and 10% trailing triggers occur after smaller underlying price movement
  than at 5x. This is a real exit-timing change and future cohorts must preserve leverage provenance.

## Evidence

- Added a launcher regression asserting both ceilings are present before the Python entry point.
- Made the snapshot-unavailable risk test independent of local leverage configuration.
- Focused suite: 42 passed.
- Full suite: 1,053 passed, one optional import-layering test skipped.

## Verdict

`KEEP — 10X SCOPED TO NEW ./lynxion VST ENTRIES`. Runtime activation requires a fresh commit-bound
forward cohort; the first new position must provide authoritative exchange readback evidence.
