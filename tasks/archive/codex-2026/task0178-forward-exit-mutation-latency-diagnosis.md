# TASK-0178 — Forward-exit mutation latency diagnosis

## Boundary

Diagnose the TASK-0177 stop-replacement failures from committed source and the
prospective event ledger only. No runtime, broker, threshold, or strategy mutation.

## Findings

### Fact

- The manager uses authoritative position leverage for ROE and skips mutation when
  leverage is missing or malformed.
- `LINKUSDT` at 2.07% and `BCHUSDT` at 1.78% were eligible through the distinct
  three-hour time-decay breakeven rule: at observed 5x leverage its fee-coverage
  threshold is 1.75%. The earlier suspicion of a 6% trigger bypass is retracted.
- A replacement attempt measures latency around the entire broker call. Observed
  response latency spans 8.7–248.3 seconds.
- Every BingX request first blocks on one process-global token bucket configured for
  only five requests per 60 seconds. The adapter's unused instance fields claim 300
  requests/minute, but do not configure that shared limiter.
- Stop replacement is synchronous and serial inside the position-evaluation loop.
  One mutation may make the remaining open-position snapshot and prices minutes old.
- A stop sync can retry three times in the manager. Each adapter call can also perform
  conflict retries, while each HTTP request can retry transient failures three times.
- The six `UNIUSDT` failures (`position not exist`) consumed about 235.5 seconds before
  evaluation moved on. Later LINK/BCH stop-price rejections are consistent with a
  price captured before a long blocking wait, and no position/mark revalidation occurs
  immediately before submission.

### Inference

The primary causal mechanism for the prospective failures is request-queue starvation
plus nested synchronous retries, which stale both position existence and stop-price
validity. Network/exchange delay may contribute, but a 10-second HTTP timeout alone
cannot explain accepted calls taking over 200 seconds; the global limiter wait is
inside the measured broker-call interval and is unbounded/fairness-free.

### Unknown

- The ledger does not separately record rate-limit queue time, HTTP time, internal
  conflict handling, and exchange processing time.
- Terminal outcomes do not yet exist, so the PnL cost of this defect is unknown.

## Verdict

`DIAGNOSED_NOT_FIXED`. This execution defect can directly invalidate evaluation of
exit-management edge and therefore precedes any 5% profit-floor experiment. A safe
fix needs deterministic tests for bounded priority mutation latency, fresh position
and mark validation immediately before submission, terminal handling of
`position not exist`, and explicit latency-stage telemetry. Deployment remains a
separate approval gate.

## Next

TASK-0179: specify the minimal fail-closed correction and regression tests without
changing policy thresholds or deploying/reloading it.
