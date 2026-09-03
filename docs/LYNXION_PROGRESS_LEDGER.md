# Lynxion Engineering Progress Ledger

## Current goal

Establish a statistically defensible, cost-adjusted trading edge while preserving execution
correctness, experimental validity, and VST risk controls.

## Current task

Hold runtime integration behind the verified P0 leverage correction; continue only C-11 collection
and non-production validation until the automation boundary authorizes risk/admission changes.

## Status

TASK 000 operational closure and TASK 001/002 attribution are complete. Controlled edge
research remains in progress; C-01 through C-26 historical candidates have not cleared their
frozen promotion gates and production strategy logic is unchanged.

## Latest verified findings

- TASK-0135 now freezes the minimal fail-closed correction boundary and its failure-injection tests,
  but implementation remains blocked by the active automation's explicit prohibition on production
  risk/admission/leverage changes.
- TASK-0135's implementation map inventories every canonical contract, live Order constructor,
  risk-adjusted clone, BingX admission/hydration boundary, and position-manager consumer. No current
  BingX leverage/margin endpoint exists locally; official semantics must be verified before coding.
- TASK-0134 implements the disconnected exit-event ledger writer/validator with atomic daily JSONL
  append, secret rejection, causal validation, corruption detection, and deterministic hashes. It is
  not imported by any runtime path and changed no production behavior.
- TASK-0133 freezes the forward exit-observability contract: append-only manager evaluations,
  stop request/response/visibility/state transitions, restart hydration, leverage readback, and exit
  fills. No trailing threshold is selected and no production path changed.
- TASK-0132 verifies a P0 fail-open leverage defect: configured `max_leverage=5.0` is absent from
  ExecutionIntent/Order/Position, BingX admission neither sets nor verifies exchange leverage,
  hydration drops it, and ActivePositionManager independently assumes 10x. A characterized 10x
  authoritative snapshot is admitted under a mocked 5x configuration. No runtime setting changed.
- Post-C27 synthesis pauses historical candidate creation: available families are rejected or
  already assigned to C-11 prospective confirmation, and no unopened mechanism currently clears
  the sequential admission gate. Next work moves to authoritative leverage correctness and the
  event observability required for a future forward profit-lock comparison.
- C-27 concentrated-aggressor exhaustion is REJECTED: 186 primary trades had -0.3418% expectancy,
  PF 0.2533, and a daily-clustered 95% interval wholly below zero. Every fold, both sides, both
  primary years, and the 2024 temporal reverse were negative; even gross expectancy before the
  frozen 0.30% cost was negative. No threshold or direction variant is admitted on this panel.
- TASK-0128's data gate is KEEP: all 972 expected official BTCUSDT aggregate-trade archives were
  checksum verified and produced 93,312 complete native 15-minute rows from 2024-01-01 through
  2026-08-29. Core integrity violations and missing intervals are zero, the normalized SHA-256 is
  `3e5975b6e1369685877c57944375a330548515ce7eb064f240b3c81885ef9edf`, and the 20 GiB storage
  reserve was preserved. No trading outcome was opened.
- TASK-0129 read-only exit audit reconstructed the latest 50 completed BingX VST positions. In a
  10x sensitivity view, 23 reached estimated MFE >=10% ROE, 19 reached >=12%, and 14 reached >=10%
  before exiting below +5% net ROE; nine finished between +2% and +5%. Forty-eight exits were
  `STOP_MARKET` and two were `TAKE_PROFIT_MARKET`. One-minute candle extremes make MFE/MAE estimates,
  not proof that the manager observed the extreme or successfully amended the exchange stop.
- BingX `allOrders` omitted historical leverage. All three currently open VST positions report 10x,
  while loaded risk settings report `max_leverage=5.0` and ActivePositionManager models ROE with a
  hard-coded default 10x. Add a separate fail-closed leverage-consistency audit; do not change live
  leverage or trailing thresholds from this diagnostic sample.

- Post-TASK-0127 synthesis retains the full-corpus NO_GO but finds a bounded BTC-only panel feasible:
  2024–2026 compressed size is 18.35 GB (~17.1 GiB). Dates and acquisition-only features are frozen
  before inspection; TASK-0128 must preserve the 20 GiB reserve and cannot define an outcome.
- TASK-0127 is NO_GO under the frozen storage gate: complete BTC/ETH aggTrades coverage exists and
  sample checksums/schema pass, but the compressed corpus is ~45.8 GiB and cannot coexist with the
  required 20 GiB reserve on ~57.9 GiB free storage. No bulk download or outcome was opened.
- Post-C26 synthesis forbids response-band/horizon/symbol variants and pauses candidate churn.
  TASK-0127 evaluates a genuinely richer aggregate-trade source using listings and minimal schema
  samples only, with a storage gate before any bulk download.
- C-26 is preregistered with outcome unopened: exact completed UTC-hour BTC shocks above causal
  p95/720 and 1.50%, same-direction alt response ratio 0–0.35, next-open directional alt entry,
  exact four-hour exit, actual funding, 0.30% cost, clustered uncertainty, and frozen gates.
- Post-C25 synthesis closes direct basis convergence and admits causal BTC-lead/alt-underreaction
  as the next distinct market-context family. No conditional membership has been computed; one
  complete specification must be frozen before evaluation.
- C-25 is preregistered with outcome unopened. It preserves C-24's p99/2,880, 0.40% floor,
  two-leg execution, convergence/timeout, funding, costs, periods, bootstrap, and gates unchanged;
  only the disjoint five-symbol universe and its breadth denominator differ.
- TASK-0123 data gate is KEEP: 6,685 checksum-verified spot archives yielded 128,346 complete
  rows per DOGE/LINK/LTC/DOT/AVAX, zero core violations, explicit maintenance gaps, and exact
  alignment of every retained timestamp to the C-22 futures panel. No C-25 outcome was opened.
- Post-C24 synthesis permits exactly one unchanged, disjoint confirmation on DOGE/LINK/LTC/DOT/
  AVAX. C-24's sparse positive cells remain rejected; no threshold, horizon, exit, cost, or symbol
  slice may change. TASK-0123 is data acquisition only and cannot open conditional outcomes.
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

- TASK-0134 disconnected ledger suite: 6 passed, covering deterministic append/validation,
  corruption, duplicates, timestamps, sensitive fields, causal references, state commits, and
  concurrent writers. Full post-task suite: 773 passed, 1 optional layering test skipped.
- TASK-0132 focused leverage/risk-admission characterization: 25 passed; the three new tests prove
  leverage is absent from Order/Position, a 10x authoritative snapshot does not fail against a
  mocked 5x configuration, and ActivePositionManager independently defaults to 10x.
- C-27 full post-outcome suite: 764 passed, 1 optional layering test skipped (`import-linter` is
  not installed locally).
- C-27 pre-outcome focused suite: 5 passed for causal threshold exclusion, signal conjunction,
  reversal direction, next-open/exact-four-hour execution, funding sign, missing paths, and costs.
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
- C-24 delta-neutral basis convergence: the frozen >0.40%/causal-p99 signal produced only seven
  primary pairs. Net expectancy was +0.1038% with a positive clustered interval, but every minimum
  sample/breadth gate failed and reverse N was only two. The sparse result is rejected and its
  threshold cannot be relaxed on the opened panel.
- C-25 unchanged independent basis convergence: only two primary pairs survived, both DOGE, with
  +0.3117% expectancy; reverse had zero pairs. Sample, breadth, concentration, PF, and reverse gates
  failed. Together with C-24, this closes direct basis convergence without threshold relaxation.
- C-26 BTC-lead/alt-underreaction: 103 primary trades, -0.2102% expectancy, PF 0.744, CI crossing
  zero, and only one positive fold. Reverse 2023 was -0.9667%, PF 0.238, with every fold/side/symbol
  negative. The frozen market-context propagation candidate is rejected.
- C-27 concentrated-aggressor exhaustion: 186 primary trades, -0.3418% expectancy, PF 0.2533,
  clustered CI fully below zero, and every fold/side/year negative. Reverse 2024 was -0.4978%,
  PF 0.1936, N=71. The exact large-trade concentration reversal is rejected without variants.

## Open risks

- Recent exit evidence is consistent with profit giveback after favorable excursion. Required
  follow-up: correlate manager evaluation timestamps, submitted/replaced stop prices, exchange order
  visibility, mark-price trigger semantics, fills/slippage, and restart hydration for each position.
  Preregister any +10/+12 trigger and +4/+5 lock comparison on a separate forward/OOS sample.
- Exchange leverage currently reports 10x on open VST positions despite a loaded 5x local risk cap;
  the authoritative leverage-set/admission path has not yet been proven fail-closed.

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

Amend the active automation boundary or provide a separate authorized task that explicitly permits
TASK-0135's production risk/admission/leverage correction. The implementation scope and mandatory
failure-injection tests are frozen; do not connect the event ledger or permit new entries first.

## Operator decision required

**NO for TASK-0106.** The operator granted standing authorization on 2026-08-29 for ordinary engineering/research,
verified commits, and controlled VST/paper runtime reloads after pre/post protection checks.
Real funds, secrets, destructive/data-loss operations, security-boundary changes, paid services,
legal/compliance decisions, and irreversible choices remain separately approval-gated. The official
free Binance archive reopens historical OI acquisition without a paid-service or execution decision.
