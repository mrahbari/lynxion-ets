# Lynxion Edge Research Decision Board

**Updated:** 2026-09-16

**Primary-family capacity:** 5 maximum

| Rank | Mechanism | Origin | Evidence | Mechanism quality | Data ready | Cost hurdle | Engineering cost | Fast falsification | Status |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | 15m mean reversion conditioned on aggressive flow | OPERATOR + CODEX + LYNXION_DATA | TASK-0369: p75 conditioning improved baseline by only +0.0039 percentage points; net expectancy -0.2881%, all folds/symbols/sides negative, bootstrap wholly below zero, p70/p80 also negative | Falsified for this specification; consistent with Phase-17 redundancy | Yes | Failed 0.30% primary and 0.50% stress | Completed with one disposable script/report | Frozen fast-falsification gates failed | REJECT |
| 2 | Funding as a state modifier | OPERATOR + CODEX | TASK-0370: broad states failed/unstable; C-12 positive but CI crossed zero; flow non-incremental; severe-tail rebound already frozen as C-11 | One narrow plausible crowding mechanism, already under the correct forward test | Yes | Existing C-11 gate governs | No new engineering justified | Do not recycle percentiles/horizons; keep C-11 sealed | COLLECTING |
| 3 | Volatility-normalized time-series momentum | OPERATOR + CODEX | TASK-0371: C-14 canonical own-series trend was negative/unstable; independent C-15 LONG clue failed confidence/fold/symbol/concentration gates | Closed; volatility scaling changes sizing rather than creating directional information | Existing data sufficient for rejection | Failed existing primary/stress robustness | No new engineering justified | Do not recycle lookback, side, volatility threshold, or sizing | REJECT |
| 4 | Liquidation/OI cascade versus exhaustion | OPERATOR + C-33 | C-33 public prospective collection is valid but requires 8,640 warmup buckets and 180 days | High causal clarity, low near-term information rate | Partial: liquidation collection exists; valid OI provenance remains constrained | Must distinguish continuation/reversal after costs and correlated-event clustering | Existing background collector; no expansion | Deprioritize if practical decision horizon remains too slow or required OI is unavailable point-in-time | MINIMAL_TEST |
| 5 | Order-flow toxicity as filter/state classifier | OPERATOR + CODEX + LYNXION_DATA | Phase-17 and C-21/C-22 rejected standalone directional flow; prior flow was weak/redundant | Low-medium only as incremental NO_TRADE/risk state | Existing taker-flow panel is ready; raw L2 is not justified | Must add OOS value beyond price/volume baseline | Low for panel test; high and prohibited for raw-L2 build | Reject if no incremental OOS information beyond baseline | PARK |

## Background frozen cohorts

| Cohort | Scientific state | Operational role |
|---|---|---|
| C-35 | `COLLECTING` | Continue unchanged to the 168-decision throughput checkpoint; not the primary discovery clock |
| C-11 | `COLLECTING` | Low-cost eight-hour funding monitor; too slow as primary path |
| C-33 | `COLLECTING` | Low-cost background collection after the verified 1,000-bucket checkpoint |

## Current single next action

Perform one bounded feasibility review of liquidation/OI cascade continuation versus forced-flow
exhaustion. Inventory C-33, prior OI/liquidation work, and available point-in-time data. Determine
whether a faster distinct question exists without altering C-33, using censored snapshots as complete
tape, or building new collection. If not, keep C-33 background-only and move on.
