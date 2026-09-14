# Edge Acceleration Decision — 2026-09-14

**Evidence boundary:** repository HEAD `539019c` plus current read-only cohort audits

**Decision:** Continue frozen collection cheaply, reject renewed carry/basis and broad L2 builds,
and immediately repair C-33 prospective collection liveness with the smallest safe change.

## Measurement conventions

- Rates are descriptive operational diagnostics, not new scientific gates.
- C-35 signals within 24 hours are one effective market episode for scheduling estimates. Its two
  signals occurred one hour apart, so raw N=2 and operational effective N=1.
- C-11 events separated by more than 24 hours are distinct operational episodes. This does not
  change its frozen event-bootstrap method.
- C-33 eligible five-minute buckets measure coverage, not independent trading events. No C-33 signal
  can exist before the frozen 8,640-bucket warmup.
- Calendar projections assume the observed rate persists and are therefore estimates, not promises.

## Active cohort rates and operational decisions

| Cohort | Observed span | Eligible/event rate | Outcome rate | Effective independent rate | Breadth | Time estimate | Operational decision |
|---|---:|---:|---:|---:|---|---|---|
| C-35 | 3.70 days | 89 decision hours; 2 signals; 0.54 signals/day | 2 complete; 100% of signals | 1 episode; 0.27/day | 2/6 symbols, SHORT only, 1 UTC week | 168-decision rate checkpoint in about 3.3 days; 240 raw signals about 445 days at observed rate | `CONTINUE` to 168; deprioritize as primary if projected effective completion remains beyond 90 days |
| C-11 | 15.24 days | 3 eligible candidates; 0.20/day | 2 complete; 0.13/day | 3 separated episodes; 0.20/day | BTC/ETH; LONG only; sparse time coverage | roughly 747 additional days to 100 completed at observed rate | `CONTINUE` cheaply but `TOO SLOW — DEPRIORITIZED AS PRIMARY PATH`; review at 30 calendar days |
| C-33 | 3.70 active-ledger days | 740 eligible buckets; about 200/day while active | 0 signals/outcomes before warmup | Not applicable yet; buckets are coverage | 6 symbols; no trade side/week breadth yet | about 1.3 active days to 1,000; about 39.5 active days to 8,640 warmup; frozen minimum also requires 180 days | `MINIMAL TEST`: restore liveness, verify one clean interval, then background `CONTINUE` |

## Material C-33 liveness finding

The latest C-33 record is approximately 4.54 days older than the current C-35 public-data coverage.
The ledger reports one unclosed active session but has not advanced beyond 740 eligible buckets.
This is not healthy collection. Starting another session without resolving the stale unclosed
session could create an invalid two-active-session state. The immediate minimal task must detect a
dead collector, close the stale session explicitly without backfill, start exactly one pinned-source
session, and verify a complete eligible interval.

## Ranked direction table

| Rank | Direction | Economic mechanism | Existing data enough? | Expected research value | Engineering cost | Time to answer | Decision |
|---:|---|---|---|---|---|---|---|
| 1 | C-33 continuation | Forced-liquidation exhaustion reversal | Yes for continued prospective collection | Medium; distinct mechanism, but long frozen horizon | Low: repair existing supervisor only | One interval for liveness; ~1.3 active days to next checkpoint | `MINIMAL TEST` |
| 2 | C-35 continuation | Compression-release continuation | Yes | Medium-high but currently sparse and concentrated | None beyond existing collector | ~3.3 days to rate checkpoint | `CONTINUE` |
| 3 | C-11 continuation | Severe negative-funding rebound | Yes | Medium but extremely slow | None beyond existing cadence | 30-day operational review; frozen N projection ~2 years | `CONTINUE` in background |
| 4 | Funding/carry and direct basis | Hedged funding persistence or basis convergence | Yes; C-23/C-24/C-25 already answer the family | Low: carry gross +0.0086% was far below cost; direct basis failed breadth twice | High if implemented safely as two legs | Already answered | `REJECT` |
| 5 | L2/microstructure | Depth/flow predicts cost-surviving direction | Sufficient for prior aggregated-depth and flow families; insufficient only for full raw book | Low: C-18/C-19 and Phase-17 were negative/redundant; C-32 had timestamp/auth feasibility blockers | High for full capture/reconstruction | Existing family evidence is sufficient to reject a platform build | `REJECT` |
| 6 | Optional new mechanism | None currently justified | No specific unopened causal mechanism | Unknown | Avoided | Not applicable | `DEFER` |

## Funding/basis feasibility verdict

`REJECT — ECONOMICS INSUFFICIENT`

C-23 evaluated 3,407 primary hedged pairs. Mean capital-normalized basis return was +0.0019% and
funding return +0.0067%, producing only +0.0086% gross carry before a 0.20% primary cost. Net
expectancy was -0.1914%, every fold and symbol was negative, and the 2023 reverse was negative.
C-24 then found only seven primary basis-convergence events; unchanged C-25 found only two, both on
DOGE, with no reverse events. Their frozen family verdict is closed/rejected. Implementing safe
spot/perp legs would add broker, hedge, reconciliation, borrow, transfer, and failure complexity
without sufficient economics.

No funding carry or direct basis strategy should be built.

## L2 information-value verdict

`LOW INFORMATION VALUE — DO NOT BUILD`

The official Binance aggregated book-depth archive was already acquired and integrity-gated. C-18
tested static near-book imbalance with 2,154 primary trades and returned -0.3568% funding-inclusive
expectancy; C-19's distinct dynamic liquidity-withdrawal mechanism also failed. Phase-17 found
directional order-flow signals negative after cost in every symbol and every fold, with no
incremental directional information beyond OHLCV. C-32 later established that its frozen BingX book
contract lacked the required per-book timestamp and newer access involved signed requests.

Full raw L2 could contain different information, but proving that would require permanent capture,
book reconstruction, storage, synchronization, and execution assumptions. Current evidence does not
justify that expansion. No temporary sample is authorized until a new, specific causal mechanism
explains why it should overcome the prior cost and redundancy failures.

## Bounded historical-loss conclusion

- Known sizing/risk defects amplified historical loss; current notional caps address the class but
  do not retroactively prove strategy profitability.
- The frozen historical aggregate remains strongly negative after recorded fees.
- Strategy economics are negative across the mixed historical population.
- Exit behavior and profit giveback are incompletely attributable because historical MFE/MAE,
  measured slippage, funding, regime, and configuration provenance are missing.
- Contributions overlap; no defensible percentage decomposition summing to 100% is available.
- `UNKNOWN` remains material. No rejected family is reopened solely from this record.

## What must not be built

- funding carry or direct basis production strategy;
- full L2 capture/reconstruction platform;
- ML, HMM/GMM, or feature-platform expansion;
- new two-leg execution/position architecture;
- paid-data integration;
- another numbered candidate without a distinct unopened causal mechanism;
- variants of C-11/C-33/C-35 or previously rejected opened panels.

## Highest-value next engineering task

**Task:** Restore the already-authorized public C-33 collector after proving no process is alive and
handling its stale unclosed session without backfill or multiple-active-session ambiguity.

**Budget:** approximately 2 source/test files, 30–80 LOC, no new service, no new dataset, no protocol
change, no production or broker path, and one task/evidence record.

**KEEP:** exactly one fresh session, pinned collector source verified, prior stale interval explicitly
ineligible, ledger append-only, no duplicate keys, one complete new eligible bucket, and the eligible
count never decreases.

**REJECT/STOP:** another process exists, source/manifest mismatch, multiple active sessions remain,
ledger mutation/backfill is required, integrity regresses, or the first complete interval cannot be
verified.

After liveness restoration, C-33 returns to low-cost background collection. The primary decision
clock remains C-35's frozen 168-decision signal-rate checkpoint.
