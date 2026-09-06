# TASK-0179 — Fail-closed stop-mutation correction contract

## Objective

Bound stop-mutation queue delay and prevent retries against a stale position/price
snapshot without changing breakeven, trailing, time-decay, leverage, or symbol policy.

## Frozen minimal design

1. The process-global exchange limiter remains the single source of total BingX
   request capacity. Do not create a second bucket or increase its capacity without
   verified exchange-limit evidence.
2. Add FIFO priority admission inside that limiter. Trade-order mutations wait ahead
   of ordinary market-data/account polling, but still consume the same tokens and
   cannot exceed the configured aggregate capacity.
3. Admission for a stop mutation is bounded. If it cannot obtain a token within the
   frozen deadline, emit an explicit failed response and defer to the next manager
   evaluation; never block the complete position loop indefinitely.
4. Classify `position not exist`, side/position mismatch, and stop-price-on-wrong-side
   responses as stale-snapshot terminal failures. Do not repeat the same request two
   more times. The next evaluation must begin with a fresh position/mark snapshot.
5. Timestamp errors may receive one newly signed retry because the adapter already
   regenerates timestamps per HTTP attempt. They must not trigger cancel-first logic.
6. Preserve cancel-and-replace only for explicit exchange position-stop conflicts.
   Never cancel a visible protective stop for queue timeout, stale position, invalid
   price, transport timeout, or ambiguous error.
7. Extend prospective telemetry with non-sensitive stage timing: limiter queue,
   HTTP/adapter, total mutation latency, terminal classification, and retry decision.
8. Local state may advance only after exchange acceptance, exact pending-order
   visibility, and `STATE_COMMITTED`, preserving the existing monotonic invariant.

## Deterministic acceptance tests

- Priority waiter precedes later ordinary waiters without exceeding bucket capacity.
- Mutation admission expires at the bounded deadline and no broker POST occurs.
- `position not exist` and wrong-side stop-price errors produce one attempt only.
- A timestamp error produces at most one newly signed retry.
- No terminal/ambiguous failure cancels the existing stop.
- A successful replacement still requires identity-aware visibility before state
  commit.
- Threshold and leverage regression tests prove policy values and ROE calculation are
  unchanged.

## Non-goals

- No 5% profit-floor policy.
- No threshold tuning or historical reslicing.
- No runner reload, broker call, or deployment.
- No increase in configured exchange request capacity in this task.

## Next

TASK-0180: implement and test this contract in the smallest source surface. Deployment
and cohort-boundary handling remain separate approval-gated tasks.
