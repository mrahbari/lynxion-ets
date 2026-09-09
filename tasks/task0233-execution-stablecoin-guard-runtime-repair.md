# TASK-0233 — Execution stablecoin guard runtime repair

## Scope

Repair the verified `NameError: filter_stablecoin_pairs is not defined` in the auto-detection
execution path. Preserve the existing stablecoin-to-stablecoin rejection policy and do not alter
strategy, leverage, position sizing, broker routing, or heartbeat safety behavior.

## Root cause

The execution method referenced two local configuration variables that were lost when the method
was mechanically extracted into its mixin. Every intent reaching that point could fail closed
before order construction, including non-stablecoin symbols.

## Change

Read both values from the already injected data settings. Normalize both the current list schema
and the legacy comma-separated representation. The downstream rejection logic is unchanged.

## Acceptance

- No free configuration variables remain in the execution-side stablecoin guard.
- Enabled/disabled settings and list/CSV schemas are covered by regression tests.
- The complete suite passes before runtime reactivation.

## Evidence

- Focused leverage/execution suite: 18 passed.
- Full suite: 1,056 passed; one optional import-layering test skipped.
- Pre-stop BingX VST audit: two open positions, two STOP_MARKET and two
  TAKE_PROFIT_MARKET protections, with no position missing either protection.

## Verdict

`KEEP — VERIFIED EXECUTION-LIVENESS DEFECT REPAIRED`. Runtime must use a new empty
commit-bound forward-exit cohort before reactivation.
