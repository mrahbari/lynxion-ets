# VST entry latency — 2026-10-07 (outcome-blind operational forensics)

Scope: local order-intent, execution-truth, and source-code evidence only. No authenticated account query, order action, runner restart, or Pilot-2 change was made for this investigation.

## Observed timings (UTC)

| Symbol | Local INTENT | Broker result recorded | Elapsed | Local result |
| --- | --- | --- | ---: | --- |
| NEARUSDT | 06:32:26.838 | 06:38:14.855 | 348.0 s | SUBMITTED |
| HYPEUSDT | 06:49:02.754 | 06:55:26.863 | 384.1 s | SUBMITTED |
| SOLUSDT | 07:04:50.740 | 07:09:02.847 | 252.1 s | SUBMITTED |

FACT: `logs/execution_truth_ledger.jsonl` records corresponding TESTNET decisions/results with `execution_latency_ms` 347880.243, 384104.888, and 252099.148. `data/live_order_journal.json` records the above INTENT/SUBMITTED times. SUBMITTED is broker acceptance, not a verified fill. The operator subsequently reported these orders visible in the broker.

FACT: The BingX adapter serializes entry admission and submission under `_BINGX_ENTRY_ADMISSION_LOCK`. For each admitted entry, it obtains an authenticated position snapshot, writes margin mode and leverage, reads both back, then submits the order. These operations all use the shared BingX limiter configured at five requests per 60 seconds. Entry calls have no limiter admission timeout. Physical retries also consume limiter capacity; protective-order requests can receive priority.

INFERENCE: Waiting for shared request capacity is a credible major contributor, especially with concurrent position/protection traffic. The existing ledger does not break total execution time into lock wait, limiter wait, network round trips, retries, and broker processing, so exact attribution is **not established**. The multi-minute interval after INTENT proves that pre-intent logging alone cannot explain this delay.

UNKNOWN: discovery-to-INTENT time, per-request limiter wait, exact exchange receipt time, exchange-side fill time, and whether every order would meet a 2–3 second acceptance target after remediation. Local FILLED status must not be conflated with broker acceptance or exchange fill timestamp.

## Safety / decision boundary

Do not bypass broker-backed position checks, isolated-margin/leverage verification, protective-order priority, or the shared limit merely to reduce latency. Removing or caching admission checks, changing limiter capacity/priority, or rejecting signals after a freshness deadline can change trade acceptance or risk and requires a separate reviewed trading-policy decision. A 2–3 second *fill* guarantee is not under local software control.

Next safe engineering unit: add networkless-tested, monotonic stage timings for discovery/queue/INTENT, entry-lock wait, limiter wait, HTTP/retry, broker acknowledgement, and subsequent fill verification; keep wall-clock provenance separately. Compare a bounded VST observation cohort before any policy change. Define an operator-approved fail-closed maximum signal age and an exchange-limit-backed request budget before activating latency remediation. Do not retry an order with unknown submission status.
