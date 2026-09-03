# TASK-0135 — Fail-Closed Authoritative Leverage Contract

**Status:** IN PROGRESS — REPOSITORY-ONLY IMPLEMENTATION AUTHORIZED

## Objective

Remove TASK-0132's verified fail-open path by making intended and exchange-reported leverage an
authoritative, fail-closed part of every BingX derivatives entry and hydrated position.

## Minimal Implementation Boundary

1. Add explicit requested leverage to the derivatives execution contract and authoritative leverage
   to hydrated Position state. Preserve compatibility for non-derivatives callers, but BingX
   derivatives entry must reject missing leverage.
2. Source intended leverage from one validated configuration value. It must be finite, >=1, and no
   greater than both configured leverage ceilings; conflicting configured ceilings fail closed.
3. Under the existing BingX entry-admission lock, validate portfolio controls, establish isolated
   margin/leverage for the requested symbol through the broker API, read authoritative state back,
   and require exact agreement before submitting the entry order.
4. Missing, malformed, stale, cross-margin, excessive, or mismatched readback rejects the entry.
   Never silently adopt exchange state and never place the entry first.
5. Existing open positions above the ceiling block new entries and raise evidence; they are not
   automatically mutated or closed.
6. Preserve authoritative leverage during hydration. ActivePositionManager must calculate ROE and
   locks from each position's authoritative leverage and skip mutation when it is unavailable;
   remove the independent 10x production default.

## Required Tests

- Configured/requested/exchange 5x agreement permits the mocked boundary.
- 5x requested versus 10x exchange, missing readback, malformed readback, conflicting ceilings,
  cross-margin state, and broker error all reject before `_execute_order_after_admission`.
- Existing excessive-leverage position blocks a different-symbol entry.
- Position hydration retains leverage and rejects malformed leverage without breaking reconciliation.
- Restarted ActivePositionManager uses hydrated leverage and never substitutes 10x.
- Non-derivatives contracts remain compatible; no leverage rule is weakened.
- Focused failure injection and full suite pass before any controlled runtime action.

## Explicit Non-Goals

- No leverage value change, automatic migration, position close, threshold adjustment, symbol-list
  change, trailing-policy change, or real/paper order is authorized by this task specification.
- No runtime implementation may begin until the active automation prohibition is amended or a
  separate authorized task supersedes it.

## Prepared Evidence

The exact domain, order-construction, BingX admission/hydration, and active-position-manager
touchpoints are inventoried in `docs/LYNXION_LEVERAGE_IMPLEMENTATION_MAP.md`. No existing BingX
leverage/margin endpoint implementation was found locally. Official BingX references now verify the
margin-mode query/set, leverage query/set, and position readback contracts; no endpoint was called.

## Implementation Progress

- The canonical execution intent/order contracts now carry optional requested leverage while
  preserving compatibility for non-derivatives callers.
- Hydrated positions now retain validated finite leverage and boolean isolated-margin state;
  malformed values remain explicitly unknown without aborting reconciliation.
- The BingX adapter's formatted order clone preserves requested leverage.
- Six focused TASK-0132/TASK-0135 contract and hydration tests pass. Entry admission, authoritative
  pre-order readback, and per-position ActivePositionManager enforcement remain unfinished.
