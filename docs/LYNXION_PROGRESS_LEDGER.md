# Lynxion Engineering Progress Ledger

## Current goal

Establish a statistically defensible, cost-adjusted trading edge while preserving execution
correctness, experimental validity, and VST risk controls.

## Current task

Implement and evaluate preregistered C-24 delta-neutral spot/perpetual basis convergence while C-11
continues prospective collection.

## Status

TASK 000 operational closure and TASK 001/002 attribution are complete. Controlled edge
research remains in progress; C-01 through C-12 historical candidates have not cleared their
frozen promotion gates and production strategy logic is unchanged.

## Latest verified findings

- C-24 is preregistered with outcome unopened: positive basis above causal prior-2,880 p99 and
  0.40%, next-open LONG spot/SHORT perpetual, causal convergence-or-24h exit, actual funding,
  two-unit capital normalization, clustered bootstrap, reverse period, and frozen stability gates.
- Post-C23 synthesis is complete. Funding-persistence variants are barred; the next admitted
  independent family is direct delta-neutral spot/perpetual basis convergence. It differs from
  directional C-20 and funding-selected C-23 and is enabled by TASK-0118's official spot panel.
- TASK-0118's official spot data gate is KEEP. C-23 is now preregistered with outcome unopened:
  equal-notional LONG spot/SHORT perpetual after causally unusual positive completed funding,
  next-open execution through the next settlement, explicit two-unit capital normalization, and
  clustered uncertainty.

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
- TASK-0100 collector suite: 680 passed, 1 optional layering test skipped; first prospective
  update correctly remained COLLECTING with N=0 and no pre-boundary leakage.
- TASK-0101 suite: 684 passed, 1 optional layering test skipped; this includes the parameterized
  funding acquisition and C-12 evaluator boundary regressions.
- TASK-0102 suite: 685 passed, 1 optional layering test skipped; C-13 reused the frozen C-12
  mechanics with only report identity and dataset paths parameterized.
- TASK-0103 suite: 689 passed, 1 optional layering test skipped; four C-14 tests cover causal
  daily aggregation, next-open entry, the fixed 28-day exit, future mutation, and costs.
- TASK-0104 suite: 692 passed, 1 optional layering test skipped; C-15 adds custom-universe
  acquisition, disjoint-universe, and pre-admission LONG filtering coverage.
- TASK-0106 suite: 697 passed, 1 optional layering test skipped; five OI acquisition tests cover
  checksum binding/resume, exact/conflicting duplicates, and optional-ratio missingness.
- TASK-0107 suite: 701 passed, 1 optional layering test skipped; four C-16 tests cover strict
  pre-decision alignment, current-observation exclusion, next-open/24h execution, funding sign,
  and cost application.
- TASK-0108 suite: 704 passed, 1 optional layering test skipped; C-17 adds new-universe
  disjointness, OI-contraction construction, and explicit acquisition-task provenance coverage.
- TASK-0109 focused suite: 12 passed. The official book-depth panel retained 380,974–381,838
  normalized five-minute rows per symbol from 8,002 checksum-verified archives, with zero final
  integrity violations. Decimal-rendered integer levels and later official fractional extra levels
  have explicit regression coverage.
- TASK-0110 focused suite: 10 passed across C-18 causality/execution and TASK-0109 acquisition
  regressions. C-18 uses strict pre-decision book alignment, causal thresholds, prior-bar 24-hour
  close, correct funding sign, and an explicit minimum-sample gate.
- TASK-0112 focused acquisition suite: 5 passed. The premium-index panel retained 205,981–233,560
  unique 15-minute rows per symbol from 14,101 checksum-verified archives, with zero core integrity
  violations and explicit unfilled source gaps.
- TASK-0114 acquisition: 8,022 checksum-verified archives produced exactly 128,352 aligned native
  15-minute taker-flow rows per symbol, with zero schema/timestamp/OHLC/flow/duplicate/gap violations.
- TASK-0118 acquisition: 8,022 checksum-verified official spot archives produced 128,346 complete
  native 15-minute rows per symbol. Core integrity violations are zero; one common partial
  maintenance candle per symbol was excluded, all 36 resulting source gaps remain explicit, and
  every retained timestamp aligns to the futures panel. The frozen data gate is KEEP.

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
- C-12 cross-symbol funding generalization: 455 trades, +0.5403% expectancy, PF 1.2763, all
  four folds and all three symbols positive, and 39.91% concentration. The bootstrap 95% lower
  bound was -0.0549%, so the preregistered confidence gate rejects despite broad stability.
- C-13 unchanged temporal generalization: 628 trades, -0.0595% expectancy and PF 0.9555 at
  0.30% cost; only two folds and XRP were positive. The later sample falsifies temporal
  stability of the base negative-funding rebound rule.
- C-14 long-horizon time-series momentum: the reverse-time period was strongly positive, but
  the primary 2023–2026 sample had 228 trades, -2.5269% expectancy, PF 0.7286, and only one
  positive fold. The signal is temporally unstable and rejected.
- C-15 independent LONG holdout: +1.4752% expectancy and PF 1.1504 over 82 trades, but CI crossed
  zero, only one adequately sampled fold was positive, only two adequately sampled symbols
  were positive, and concentration exceeded its ceiling. Rejected for robustness.
- C-16 OI-confirmed impulse: 2,471 primary trades, -0.1763% funding-inclusive expectancy,
  PF 0.8818, all four folds negative, only XRP positive, and reverse-time expectancy negative.
  The intended OI expansion/continuation mechanism is rejected.
- C-17 OI-flush reversal: 2,124 primary trades, -0.3546% expectancy, PF 0.7983, CI fully below
  zero, and every fold/side/symbol negative. A new universe independently rejects the distinct
  OI contraction/reversal mechanism.
- C-18 near-book depth continuation: 2,154 primary trades, -0.3568% funding-inclusive expectancy,
  PF 0.7685, CI fully below zero, and every fold/side/symbol negative. The 2023 temporal reverse
  sample was also negative (-0.2313%, PF 0.8230, N=726). This exact L2 continuation mechanism is
  rejected without post-result slicing.
- C-19 liquidity-withdrawal differential: 1,973 primary trades, -0.3533% expectancy, PF 0.7720,
  CI fully below zero, every fold and both sides negative, and only ETH positive. The temporal
  reverse was also negative (-0.3631%, PF 0.7368, N=668). The dynamic near-book mechanism is closed.
- C-20 symmetric premium-basis convergence: 1,264 primary trades, -0.2721% funding-inclusive
  expectancy, PF 0.8125, and every fold/side/symbol negative. The 2023 reverse sample was positive
  (+0.2649%, PF 1.2297, N=490), so the mechanism is temporally unstable and rejected.
- C-21 aggressive taker-flow continuation: 2,326 primary trades, -0.2086% expectancy, PF 0.8384,
  CI fully below zero, and all four folds negative. Reverse-time was also negative (-0.3853%,
  PF 0.6827, N=831); narrow LONG/ETH cells are diagnostic only and not promoted.
- C-22 independent taker-flow confirmation: 1,928 primary trades, -0.1770% expectancy, PF 0.8906,
  only 2/4 folds and 1/5 symbols positive; reverse was -0.4288% with PF 0.7015. This second disjoint
  failure closes taker-flow continuation under the sequential policy.
- C-23 delta-neutral positive-funding carry: 3,407 primary pairs, -0.1914% net expectancy at the
  frozen 0.20% capital cost, PF 0, clustered CI fully negative, and every fold/symbol negative.
  Gross basis plus funding was only +0.0086%; reverse 2023 was also negative (-0.1902%, N=1,033).
  The unlevered next-settlement carry mechanism is rejected as economically unable to clear costs.

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
- TASK-0109 retained the official ten-level historical book-depth panel. The archive later adds
  `-0.20/+0.20` levels; they are censused but excluded from the frozen panel. Cadence gaps remain
  explicit and no observations are synthesized.
- Existing project-context documents outside the active task/ledger may contain stale claims.

## Next task

Implement C-24 exactly as preregistered, cover causal/two-leg mechanics with focused regressions,
then open the primary and reverse outcomes once and issue the frozen verdict.

## Operator decision required

**NO for TASK-0106.** The operator granted standing authorization on 2026-08-29 for ordinary engineering/research,
verified commits, and controlled VST/paper runtime reloads after pre/post protection checks.
Real funds, secrets, destructive/data-loss operations, security-boundary changes, paid services,
legal/compliance decisions, and irreversible choices remain separately approval-gated. The official
free Binance archive reopens historical OI acquisition without a paid-service or execution decision.
