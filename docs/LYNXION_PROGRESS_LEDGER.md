# Lynxion Engineering Progress Ledger

## Current goal

Establish a statistically defensible, cost-adjusted trading edge while preserving execution
correctness, experimental validity, and VST risk controls.

## Current task

Controlled evaluation of the remaining preregistered candidates after C-04 rejection, with
TASK 000 runtime reload evidence still open.

## Status

In progress. The broad ground-truth audit is complete enough to identify the next engineering
phase, but TASK 000 cannot close until generic VST profit-lock behavior is evidenced for all
qualifying positions after the corrected runner has loaded.

## Latest verified findings

- The VST portfolio has exchange-side SL/TP coverage, but this alone does not prove profit
  locks are correct.
- AVAXUSDT SHORT moved from an unlocked stop at 7.700 to 7.357 below its 7.553 entry without
  a symbol-specific manual update.
- ZECUSDT, CCUSDT, AAVEUSDT, UNIUSDT, and ONDOUSDT were observed above the configured trigger
  thresholds while their stops remained unlocked.
- The manager now waits for broker-side order visibility before local success, starts its loop
  after `is_running` is set, isolates broker failures, prioritizes BingX VST, and hydrates the
  exchange stop after a restart.
- Latest read-only VST coverage check: 11 open positions, each with one exchange-side
  `STOP_MARKET` and one `TAKE_PROFIT_MARKET` order. Coverage is not treated as proof of
  a profit lock.
- A runtime telemetry API drift prevented execution intents from reaching the broker call:
  `EnhancedLogger.log_strategy_to_broker_flow` was called but not implemented. The minimal
  logger-contract repair is locally verified; runtime reload evidence remains pending.

## Changes made

- `8c09624` verify pending exchange stops before local success.
- `43afd7b` start background protection loops reliably.
- `8cd80e1` isolate non-primary broker failures.
- `25d069f` prioritize BingX VST protection checks.
- `f649444` hydrate existing exchange stops after restart.

## Test evidence

- Focused active-position regression tests: 11 passed after the restart-hydration correction.
- Full post-correction suite: 622 passed, 1 optional layering test skipped
  (`import-linter` is not installed locally). This includes 461 unit, 109
  characterization/contract, and 52 smoke/E2E tests.
- Post telemetry-contract repair suite: 623 passed, 1 optional layering test skipped.

## Rejected hypotheses

- Higher win rate alone is not evidence of an edge.
- Adding new strategies, ML, or capital scaling before attribution/OOS evidence is not justified.

## Open risks

- The running VST process must load the latest commits before their exchange-side effect can be
  observed: PID 91102 began at 16:23, before the final protection commits at 16:34–16:49.
- Restart persistence is achieved by broker-state hydration rather than a durable manager-state
  file; the behavior needs VST evidence.
- Existing project-context documents contain stale operational and test-status claims.
- The running VST process has not yet demonstrated that execution intents pass the repaired
  strategy-to-broker telemetry call after a code reload.

## Next task

TASK 001 and TASK 002 are complete. The next task is a newly versioned, pre-registered,
chronological OOS evaluation of C-01/C-02/C-03. C-04 VWAPReversal was rejected with zero of
four positive folds after costs. Research remains isolated from the production execution path.

## Operator decision required

No for ordinary engineering/research work. A controlled runner restart or any direct external
order mutation remains an external operational action.
