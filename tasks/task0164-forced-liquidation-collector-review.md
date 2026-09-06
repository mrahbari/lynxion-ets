# TASK-0164 — Forced-Liquidation Collector Review

**Status:** COMPLETE — ACTIVATION APPROVAL GATE

## Objective

Independently review C-33 stream/schema, identity, boundary, interruption, and failure semantics
before any public connection.

## Findings and Corrections

- The frozen combined public stream URL and official `forceOrder` fields match the parser. Strict
  `st=1`, symbol/pair, FILLED, event/trade time, and closed one-minute kline checks fail closed.
- Review found that raw numeric formatting could give one semantic snapshot two keys (`2` versus
  `2.00`). Identity now canonicalizes filled quantity and average price before constructing the
  frozen key, without changing any signal parameter.
- Original and accumulated filled quantity are now both positive and a fill exceeding original
  quantity is rejected. Boundary validation is repeated at append time, including existing rows.
- A connection failure or timeout always emits an `ENDED` lifecycle record and terminates; there is
  no silent reconnect that could falsely classify a five-minute bucket as continuous. A later
  process restart receives a new session ID and overlapping buckets remain ineligible.
- Nine focused tests and the full 912-test suite pass with one optional import-linter skip.

## Activation Gate

Continuous prospective evidence requires starting a dedicated long-lived public-data process and
writing a new activation manifest. The current heartbeat explicitly prohibits starting a runtime.
No connection or manifest was created. Operator authorization is required before TASK-0165 may
start this standalone research collector; authorization would not permit orders, authentication,
broker calls, production integration, or outcome evaluation.
