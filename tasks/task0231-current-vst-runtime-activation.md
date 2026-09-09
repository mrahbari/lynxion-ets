# TASK-0231 — Current VST runtime activation

## Scope

Start the latest reviewed source on the configured BingX VST account after operator request,
without importing the prior forward-exit cohort or changing trading configuration.

## Evidence

- Duplicate-runner preflight found no active trading runner.
- Broker settings: paper false, BingX testnet true, BingX placement enabled, enabled brokers
  exactly `[bingx]`, configured leverage 5x.
- Pre-start VST audit: one open position, one STOP_MARKET, one TAKE_PROFIT_MARKET, no missing
  exchange-side SL/TP.
- The default forward-exit root correctly rejected commit drift before runtime startup and sent
  no order.
- A new empty root `data/observability/forward_exit/task0231-88f88e7` was activated at
  `2026-09-09T16:17:28.531614+00:00`, bound to commit
  `88f88e7bb873db24cf322e9fd4a2a4a09bfdb80f`, with historical import disabled.
- Runtime preflight reported `mode=TESTNET`, `ok=True`, and `live_trading=False`.
- Post-start VST audit remained fully protected. The forward observer hydrated the existing
  XRPUSDT stop and recorded a manager evaluation in the new cohort.
- CCUSDT and HYPEUSDT were rejected for excessive missing history; XMRUSDT remained blacklisted.
  These are fail-closed exclusions, not evidence of edge.

## Verdict

`ACTIVE — BINGX VST ONLY`. New automated test-account activity is operational/research input and
does not become valid edge evidence unless admitted by a preregistered cohort.
