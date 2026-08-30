# Lynxion Engineering Progress Ledger

## Current goal

Establish a statistically defensible, cost-adjusted trading edge while preserving execution
correctness, experimental validity, and VST risk controls.

## Current task

Freeze and start a no-order prospective cohort for the post-C-10 high-severity funding lead.

## Status

TASK 000 operational closure and TASK 001/002 attribution are complete. Controlled edge
research remains in progress; C-01 through C-04 are rejected and production strategy logic is
unchanged.

## Latest verified findings

- Generic profit-lock behavior was observed after runtime reload on ETHUSDT and BNBUSDT:
  their exchange-side stops moved beyond entry in the profitable direction without manual or
  symbol-specific intervention.
- The manager now waits for broker-side order visibility before local success, starts its loop
  after `is_running` is set, isolates broker failures, prioritizes BingX VST, and hydrates the
  exchange stop after a restart.
- Latest read-only VST coverage check: 10 open positions, each with one exchange-side
  `STOP_MARKET` and one `TAKE_PROFIT_MARKET` order. Coverage is not treated as proof of
  a profit lock.
- Final entry admission now reads authoritative BingX positions and atomically enforces
  capacity, duplicate-symbol, exposure, cooldown, order-risk, and stop requirements at the
  broker boundary. A dry live check failed closed at the configured 10-position capacity.

## Changes made

- `8c09624` verify pending exchange stops before local success.
- `43afd7b` start background protection loops reliably.
- `8cd80e1` isolate non-primary broker failures.
- `25d069f` prioritize BingX VST protection checks.
- `f649444` hydrate existing exchange stops after restart.
- `700c748` enforce dynamic blacklist at the final broker boundary.
- `b7cc9c3` keep the empty-opportunity loop idle-safe.
- `7418c7d` enforce broker-backed final entry risk admission.

## Test evidence

- Focused active-position regression tests: 11 passed after the restart-hydration correction.
- Full post-correction suite: 622 passed, 1 optional layering test skipped
  (`import-linter` is not installed locally). This includes 461 unit, 109
  characterization/contract, and 52 smoke/E2E tests.
- Final TASK-0092 suite: 637 passed, 1 optional layering test skipped; this includes four
  focused C-01/C-02/C-03 evaluator regressions.
- Final TASK-0093 suite: 642 passed, 1 optional layering test skipped; this includes five
  focused cross-sectional leakage/execution regressions.
- TASK-0094 acquisition suite: 646 passed, 1 optional layering test skipped; this includes four
  pagination/range/integrity regressions.
- TASK-0095 suite: 651 passed, 1 optional layering test skipped; this includes five C-06
  point-in-time/execution regressions.
- TASK-0096 suite: 656 passed, 1 optional layering test skipped; this includes five C-07
  causality/state/execution regressions.
- TASK-0097 suite: 661 passed, 1 optional layering test skipped; this includes five C-08
  causality/pair-execution regressions.
- TASK-0098 suite: 667 passed, 1 optional layering test skipped; this includes the parameterized
  holdout acquisition and five C-09 causality/execution regressions.
- TASK-0099 suite: 676 passed, 1 optional layering test skipped; this includes four funding
  acquisition and five C-10 causal/economic regressions.

## Rejected hypotheses

- Higher win rate alone is not evidence of an edge.
- Adding new strategies, ML, or capital scaling before attribution/OOS evidence is not justified.
- C-04 VWAP reversal: all four folds, all symbols, and both sides were negative after costs.
- C-01 trend BUY and C-03 volatility breakout: negative aggregate expectancy and failed
  stability gates.
- C-02 trend SELL: positive aggregate expectancy (+0.5389%, N=17) but insufficient fold
  samples, negative BTC expectancy, and ETH dependence; rejected for robustness.
- C-05 cross-sectional momentum: only 9 completed trades survived the frozen 30-symbol
  alignment rule; expectancy -3.8162%, PF 0.1982, and 95% cluster CI crosses zero. Rejected
  without lowering the threshold post-result.
- C-06 market-neutral extreme reversal: 15,810 pairs, -0.2999% net expectancy, PF 0.1345,
  bootstrap CI entirely negative, all folds/sides/symbols negative. Gross expectancy is
  effectively zero and the candidate is rejected.
- C-07 volume-confirmed acceleration: 8,245 trades, -0.2834% net expectancy, PF 0.6331,
  confidence interval entirely negative, all folds/sides/symbols/volume buckets negative.
- C-08 daily relative-strength pair: 559 pairs, -0.0738% net expectancy and PF 0.9124 at
  primary cost; only one fold positive. LONG/BTC-positive cells are clues discovered post-result
  and cannot be validated by re-slicing the same four folds.
- C-09 independent long/BTC-positive holdout: 135 trades, -0.3000% net expectancy, PF 0.8854,
  only one positive fold, and effectively zero gross expectancy. The C-08 clue did not reproduce.
- C-10 causal extreme-negative funding: aggregate +0.2008%, PF 1.1175, and all four folds
  positive, but CI crosses zero and ETH is slightly negative. Frozen gate rejects; post-result
  severity >=2 is retained only for a new prospective cohort.

## Open risks

- The current historical files do not provide point-in-time funding or bid/ask observations;
  frozen cost assumptions must remain explicit.
- Initial candidates have small samples under path-dependent execution; positive-looking narrow
  cells cannot be promoted without robust OOS support.
- The stored 15m universe is fragmented: 915/920 four-hour decision timestamps failed C-05's
  preregistered minimum of 30 symbols after contiguous-history validation.
- The existing `fetch_long_history.py`/`BinanceClient` path calls Spot `/api/v3/klines`, not
  USDT-margined perpetual futures; it cannot silently supply the next futures experiment.
- TASK-0094 acquired 128,352 exactly aligned native futures 15m bars per symbol across six
  majors (2023-01-01 through 2026-08-29), with zero gaps or integrity violations.
- Existing project-context documents outside the active task/ledger may contain stale claims.

## Next task

Register C-11 severity >=2 before collecting another observation, then run a shadow-only
funding/outcome ledger. It must place no orders and must not block other engineering research.

## Operator decision required

The operator granted standing authorization on 2026-08-29 for ordinary engineering/research,
verified commits, and controlled VST/paper runtime reloads after pre/post protection checks.
Real funds, secrets, destructive/data-loss operations, security-boundary changes, paid services,
legal/compliance decisions, and irreversible choices remain separately approval-gated.
