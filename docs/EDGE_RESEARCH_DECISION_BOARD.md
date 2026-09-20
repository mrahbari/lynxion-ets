# Lynxion Edge Research Decision Board

**Updated:** 2026-09-19

**Primary-family capacity:** 5 maximum

| Rank | Mechanism | Origin | Evidence | Mechanism quality | Data ready | Cost hurdle | Engineering cost | Fast falsification | Status |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | 15m mean reversion conditioned on aggressive flow | OPERATOR + CODEX + LYNXION_DATA | TASK-0369: p75 conditioning improved baseline by only +0.0039 percentage points; net expectancy -0.2881%, all folds/symbols/sides negative, bootstrap wholly below zero, p70/p80 also negative | Falsified for this specification; consistent with Phase-17 redundancy | Yes | Failed 0.30% primary and 0.50% stress | Completed with one disposable script/report | Frozen fast-falsification gates failed | REJECT |
| 2 | Funding as a state modifier | OPERATOR + CODEX | TASK-0370: broad states failed/unstable; C-12 positive but CI crossed zero; flow non-incremental; severe-tail rebound already frozen as C-11 | One narrow plausible crowding mechanism, already under the correct forward test | Yes | Existing C-11 gate governs | No new engineering justified | Do not recycle percentiles/horizons; keep C-11 sealed | COLLECTING |
| 3 | Volatility-normalized time-series momentum | OPERATOR + CODEX | TASK-0371: C-14 canonical own-series trend was negative/unstable; independent C-15 LONG clue failed confidence/fold/symbol/concentration gates | Closed; volatility scaling changes sizing rather than creating directional information | Existing data sufficient for rejection | Failed existing primary/stress robustness | No new engineering justified | Do not recycle lookback, side, volatility threshold, or sizing | REJECT |
| 4 | Liquidation/OI cascade versus exhaustion | OPERATOR + C-33 | TASK-0372: historical OI has no overlap with C-33; C-16 continuation and C-17 exhaustion both failed; C-33 has 1,034/8,640 warmup buckets | High causal clarity but unusably low near-term information rate | No causal combined OI/liquidation panel; censored C-33 continues forward only | Existing tests failed costs; C-33 frozen gate governs | No new engineering justified | Do not backfill, proxy, retune, or create another slow collector | TOO_SLOW / DEPRIORITIZE |
| 5 | Order-flow toxicity as filter/state classifier | OPERATOR + CODEX + LYNXION_DATA | TASK-0373: Phase-17 directly found no incremental value or liquidity-gate rescue; C-21/22/27/34 failed; TASK-0369 conditioning was non-incremental | Existing representation is weak and OHLCV-redundant; true VPIN/L2 is a different unavailable information set | Existing panel sufficient for rejection; raw L2 is unjustified | Failed direction, state gating, disjoint universe, concentration, cross-venue, and reversal conditioning | No new engineering justified | Do not retune thresholds or post-hoc filter a negative baseline | REJECT |

## Background frozen cohorts

| Cohort | Scientific state | Operational role |
|---|---|---|
| C-35 | `TOO_SLOW / COLLECTING` | The frozen rate gate projects 1,010 days to 240 outcomes; continue unchanged in the background only |
| C-11 | `COLLECTING` | Low-cost eight-hour funding monitor; too slow as primary path |
| C-33 | `COLLECTING` | Low-cost background collection after the verified 1,000-bucket checkpoint |

## Bounded-cycle portfolio verdict

`CURRENT_INFORMATION_SET_INSUFFICIENT` — C-11 is the only surviving directional hypothesis, but its
five completed outcomes are far below the frozen 100-total/30-per-symbol gate and are
ETH-concentrated. Lead B failed costs, Funding Settlement failed its materiality gate, C-35 is too
slow, and Lead A lacks provenance. No edge is identified or promotable, and no sixth historical
family is justified without genuinely new information and an unopened boundary.

## Current single next action

TASK-0414 proves API acceptance/readback and clean cancellation for a 19.96502-USDT non-marketable
DOGE LIMIT, but the operator did not see it in the BingX VST UI. UI-account identity and the complete
runner/journal/Telegram path remain unverified. The operator will start the runner later; no further
authenticated action is authorized meanwhile. This is execution correctness, not edge evidence.
