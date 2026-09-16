# Lynxion Edge Research Decision Board

**Updated:** 2026-09-16

**Primary-family capacity:** 5 maximum

| Rank | Mechanism | Origin | Evidence | Mechanism quality | Data ready | Cost hurdle | Engineering cost | Fast falsification | Status |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | 15m mean reversion conditioned on aggressive flow | OPERATOR + CODEX + LYNXION_DATA | Phase-17 found small sign-consistent reversal IC but about 58% flow/return correlation and no prior cost-surviving standalone flow edge | Medium: forced/aggressive flow may identify exhaustion, but redundancy is the central risk | Yes: six-symbol 15m futures panel, 128,352 rows/symbol, zero gaps/flow violations | Must beat the identical mean-reversion baseline after 0.30% primary and 0.50% stress round-trip costs | Low: 1 disposable script, 1 report, tests; no new data/service | Reject if flow conditioning does not add stable chronological OOS net expectancy versus baseline, is cost-negative, or is concentrated | MINIMAL_TEST |
| 2 | Funding as a state modifier | OPERATOR + CODEX | C-11 and Phase-17 show sparse rebound clues; carry/basis itself was rejected | Medium-low until incremental information is separated from reversal/flow | Yes for six symbols and historical settlements | Increment must survive full directional costs and funding itself | Low-medium; reuse panels | Reject if incremental OOS value is absent or merely re-slices the same event | PREREGISTER_NEXT |
| 3 | Volatility-normalized time-series momentum | OPERATOR + CODEX | Prior momentum families were generally cost/turnover sensitive; cross-sectional momentum stays closed | Medium if own-series trend and low-turnover state are genuinely distinct | Mostly yes | Positive at 0.30% primary and 0.50% stress with funding | Low-medium | Reject on negative net OOS, unstable folds, or reopening a rejected family by threshold variation | PARK |
| 4 | Liquidation/OI cascade versus exhaustion | OPERATOR + C-33 | C-33 public prospective collection is valid but requires 8,640 warmup buckets and 180 days | High causal clarity, low near-term information rate | Partial: liquidation collection exists; valid OI provenance remains constrained | Must distinguish continuation/reversal after costs and correlated-event clustering | Existing background collector; no expansion | Deprioritize if practical decision horizon remains too slow or required OI is unavailable point-in-time | COLLECTING |
| 5 | Order-flow toxicity as filter/state classifier | OPERATOR + CODEX + LYNXION_DATA | Phase-17 and C-21/C-22 rejected standalone directional flow; prior flow was weak/redundant | Low-medium only as incremental NO_TRADE/risk state | Existing taker-flow panel is ready; raw L2 is not justified | Must add OOS value beyond price/volume baseline | Low for panel test; high and prohibited for raw-L2 build | Reject if no incremental OOS information beyond baseline | PARK |

## Background frozen cohorts

| Cohort | Scientific state | Operational role |
|---|---|---|
| C-35 | `COLLECTING` | Continue unchanged to the 168-decision throughput checkpoint; not the primary discovery clock |
| C-11 | `COLLECTING` | Low-cost eight-hour funding monitor; too slow as primary path |
| C-33 | `COLLECTING` | Low-cost background collection after the verified 1,000-bucket checkpoint |

## Current single next action

Perform one bounded `EXPLORATORY` feasibility comparison of the identical 15-minute mean-reversion
events with and without a causal aggressive-flow condition. Reuse the six-symbol normalized futures
panel. Do not download data or build infrastructure.

The analysis must compare incremental—not standalone—value using chronological folds, full cost and
stress cost, symbol/time-event clustering, concentration, and small perturbations. A positive
exploratory result can only justify a frozen independent preregistration; it cannot prove edge.
