# Lynxion Edge Research Decision Board

**Updated:** 2026-09-16

**Primary-family capacity:** 5 maximum

| Rank | Mechanism | Origin | Evidence | Mechanism quality | Data ready | Cost hurdle | Engineering cost | Fast falsification | Status |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | 15m mean reversion conditioned on aggressive flow | OPERATOR + CODEX + LYNXION_DATA | TASK-0369: p75 conditioning improved baseline by only +0.0039 percentage points; net expectancy -0.2881%, all folds/symbols/sides negative, bootstrap wholly below zero, p70/p80 also negative | Falsified for this specification; consistent with Phase-17 redundancy | Yes | Failed 0.30% primary and 0.50% stress | Completed with one disposable script/report | Frozen fast-falsification gates failed | REJECT |
| 2 | Funding as a state modifier | OPERATOR + CODEX | TASK-0370: broad states failed/unstable; C-12 positive but CI crossed zero; flow non-incremental; severe-tail rebound already frozen as C-11 | One narrow plausible crowding mechanism, already under the correct forward test | Yes | Existing C-11 gate governs | No new engineering justified | Do not recycle percentiles/horizons; keep C-11 sealed | COLLECTING |
| 3 | Volatility-normalized time-series momentum | OPERATOR + CODEX | Prior momentum families were generally cost/turnover sensitive; cross-sectional momentum stays closed | Medium if own-series trend and low-turnover state are genuinely distinct | Mostly yes | Positive at 0.30% primary and 0.50% stress with funding | Low-medium | Reject on negative net OOS, unstable folds, or reopening a rejected family by threshold variation | MINIMAL_TEST |
| 4 | Liquidation/OI cascade versus exhaustion | OPERATOR + C-33 | C-33 public prospective collection is valid but requires 8,640 warmup buckets and 180 days | High causal clarity, low near-term information rate | Partial: liquidation collection exists; valid OI provenance remains constrained | Must distinguish continuation/reversal after costs and correlated-event clustering | Existing background collector; no expansion | Deprioritize if practical decision horizon remains too slow or required OI is unavailable point-in-time | COLLECTING |
| 5 | Order-flow toxicity as filter/state classifier | OPERATOR + CODEX + LYNXION_DATA | Phase-17 and C-21/C-22 rejected standalone directional flow; prior flow was weak/redundant | Low-medium only as incremental NO_TRADE/risk state | Existing taker-flow panel is ready; raw L2 is not justified | Must add OOS value beyond price/volume baseline | Low for panel test; high and prohibited for raw-L2 build | Reject if no incremental OOS information beyond baseline | PARK |

## Background frozen cohorts

| Cohort | Scientific state | Operational role |
|---|---|---|
| C-35 | `COLLECTING` | Continue unchanged to the 168-decision throughput checkpoint; not the primary discovery clock |
| C-11 | `COLLECTING` | Low-cost eight-hour funding monitor; too slow as primary path |
| C-33 | `COLLECTING` | Low-cost background collection after the verified 1,000-bucket checkpoint |

## Current single next action

Perform one bounded feasibility review of volatility-normalized own-series time-series momentum.
Inventory prior momentum results and identify whether a causally distinct, lower-turnover mechanism
remains testable with existing data. Do not reopen rejected cross-sectional momentum or create a
threshold variant of an opened candidate. Build nothing unless the review identifies a distinct
mechanism and a cheap falsification test.
