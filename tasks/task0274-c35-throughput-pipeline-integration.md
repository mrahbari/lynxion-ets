# TASK-0274 — C-35 throughput pipeline integration

## Scope

Make the non-economic signal-pace check an automatic final stage of the tested hourly public
pipeline.

## Contract

- Run throughput only after all activation, collection, ledger, decision, outcome, and aggregate
  stages pass.
- Preserve first-failure termination and JSON-only stage results.
- Keep the 168-decision interpretation boundary and all aggregate economics sealed.
- Add no broker, authentication, order, runtime, configuration, or strategy capability.

## Evidence

The exact-order regression now freezes eleven stages. The first combined run with throughput passes
and reports zero signals without inventing a duration estimate.

## Verdict

`KEEP — SIGNAL FEASIBILITY NOW MONITORED AUTOMATICALLY EACH HOUR`.
