# TASK-0223 — Investor release track

## Scope

Freeze a bounded initial investor-release roadmap without changing runtime, strategy,
risk, broker configuration, or prospective candidate rules.

## Decision

Investor delivery is separated from durable-edge validation. The initial artifact is a
VST/shadow technical release with honest profitability limitations. Avoidable loss paths
are prioritized before presentation work, while positive expectancy remains an evidence
gate rather than a release promise.

## Cleanup rule

Code cleanup is admitted only after a dead-code inventory proves each target unused and
regressions protect dynamic discovery paths. Cleanup stays isolated from behavioral fixes
and is never allowed to delay P0/P1 closure or edge measurement.

## Acceptance

- Release objective, evidence labels, loss-containment priorities, hygiene constraints,
  ordered tasks, and verdicts are frozen in `docs/INVESTOR_RELEASE_ROADMAP.md`.
- C-11 and C-33 remain unchanged long-horizon R&D tracks.
- No code, runtime, broker, order, account, strategy, risk, or cohort state changed.

## Next

TASK-0224: reconcile current code/tests/evidence against the investor scope and produce
the minimum release blocker set before implementing any fix or cleanup.
