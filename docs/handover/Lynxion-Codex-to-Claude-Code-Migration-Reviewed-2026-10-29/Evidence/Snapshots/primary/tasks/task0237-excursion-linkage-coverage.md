# TASK-0237 — Excursion linkage coverage

## Scope

Measure whether the existing 98-position BingX candle-excursion diagnostic can be joined to the
immutable investor baseline without heuristic or many-to-one matching.

## Contract

A position links only when canonical symbol, canonical side, exact entry timestamp, exact decimal
entry price, and exact decimal quantity identify exactly one final journal record. Zero matches,
multiple matches, or missing excursion values are rejected and counted.

## Evidence

- Frozen baseline final records: 1,257.
- Diagnostic positions: 98.
- Unique exact links: 98 (100% of the diagnostic sample).
- Unmatched: 0; ambiguous: 0; missing MFE/MAE: 0.
- Three focused regressions verify exact linking, ambiguity rejection, and missing-excursion
  rejection.

## Interpretation

The 98 recent excursion estimates now have deterministic baseline identities. This removes the
linkage uncertainty identified in TASK-0236 for this bounded subset, but does not expand coverage
beyond 98/1,257 baseline trades and does not cure candle-extreme execution uncertainty or missing
broker-reported historical leverage.

## Verdict

`KEEP — 98/98 DIAGNOSTIC LINKS VERIFIED; EDGE AND EXIT POLICY REMAIN UNPROVEN`.
