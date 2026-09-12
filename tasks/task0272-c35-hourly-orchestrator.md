# TASK-0272 — C-35 hourly public orchestrator

## Scope

Replace error-prone manual sequencing with one fail-closed public-only command, without adding any
broker, authentication, order, runtime, or production capability.

## Contract

- Run candle, funding, and aggregate activation preflights before network collection.
- Collect only public unauthenticated C-35 candles/funding.
- Verify both ledgers before appending decisions, signals, or outcomes.
- Resolve outcomes before invoking the still-sealed aggregate evaluator.
- Stop at the first non-zero or non-JSON stage; preserve explicit append flags and frozen rules.

## Evidence

Four focused tests freeze exact stage order, first-failure stop, invalid-output rejection, and safe
help behavior. The combined command passed all ten live stages in its first public-only run.

## Verdict

`KEEP — ONE FAIL-CLOSED PUBLIC-ONLY HOURLY ENTRYPOINT READY`.
