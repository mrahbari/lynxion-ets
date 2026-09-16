# Liquidation/OI Cascade-versus-Exhaustion Feasibility — 2026-09-16

## Question

Can Lynxion answer a faster, causally distinct liquidation/OI continuation-versus-exhaustion
question with existing point-in-time data, without changing frozen C-33, pretending its censored
snapshot feed is a complete liquidation tape, or building another collector?

## Existing evidence

- The official historical five-minute OI panel is high quality and covers six symbols through
  epoch `1788047700`, but it ends before C-33's prospective boundary and therefore has no temporal
  overlap with C-33 observations.
- C-16 already tested OI-confirmed price-impulse continuation. Its 2,471 primary trades had
  -0.1763% funding-inclusive expectancy and PF 0.8818; every chronological fold was negative.
- C-17 already tested OI-contraction exhaustion reversal. Its 2,124 primary trades had -0.3546%
  expectancy, PF 0.7983, a wholly negative clustered interval, and every fold/symbol/side negative.
- Binance Data Vision has no official historical forced-liquidation archive. C-33 therefore uses a
  forward-only public `!forceOrder@arr` stream that is explicitly a censored latest-snapshot feed.
- C-33 has 1,034 eligible completed five-minute buckets, still far below its frozen 8,640-bucket
  warmup. It cannot emit or evaluate a signal before that gate, and its 180-day/300-outcome gate
  makes it unsuitable as the near-term discovery clock.

## Information and engineering assessment

Existing OI and liquidation data cannot be joined causally: the historical OI panel ends before the
forward liquidation ledger begins. Creating a combined forward OI/liquidation cohort would require
new collection and at least a new warmup horizon; it would not answer the question faster. Backfill,
proxy liquidation labels, or outcome inspection before C-33's gate would weaken provenance or
corrupt the frozen protocol.

The continuation and exhaustion directions have also each received a broad, cost-aware OI-only
test and failed. Threshold, horizon, side, or percentile variants would recycle opened evidence
rather than establish a new mechanism.

## Decision

`TOO SLOW — DEPRIORITIZE NEW LIQUIDATION/OI TEST; CONTINUE C-33 UNCHANGED IN BACKGROUND`.

No new candidate, collector, data source, or production component is justified. Reconsider only
after C-33 reaches its frozen gate or a trustworthy point-in-time source creates a genuinely new
overlapping information set.

## Operational note

The read-only C-33 audit initially found 1,034 eligible buckets and zero active collection sessions.
The already-authorized public-only supervisor was resumed without backfill; a second audit confirms
exactly one active session and a fresh public heartbeat. This is operational recovery, not edge
evidence, and the missing interval remains ineligible.
