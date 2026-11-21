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
- Added an economic-contract regression proving the default 10x path activates breakeven at 6% ROE,
  sets the stop at +0.35% price, and activates trailing at 10% ROE with about 4.95% ROE locked.
- The regression exposed binary-float boundary drift that could defer an exact-threshold activation
  by one management cycle. Threshold comparisons now accept numerically equal boundary values.
- Made the snapshot-unavailable risk test independent of local leverage configuration.
- Focused suite: 42 passed.
- Final focused exit/leverage suite: 31 passed.
- Final full suite: 1,054 passed, one optional import-layering test skipped.

## Verdict

`KEEP — 10X SCOPED TO NEW ./lynxion VST ENTRIES; EXIT CONTRACT VERIFIED`. The first new position
must still provide authoritative exchange readback evidence.
