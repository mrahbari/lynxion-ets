# TASK-0165 — Forced-Liquidation Collector Activation

**Status:** ACTIVE — COLLECTING

## Authorization

The operator explicitly authorized all remaining in-scope work and requested uninterrupted
continuation. This activation remains limited to unauthenticated public market data: no broker,
account, order, strategy, risk, leverage, trailing, or production path is imported or called.

## Activation

- Active manifest boundary: `2026-09-06T11:35:35Z` (`1788694535`).
- Collector source commit: `1c46d42ff4b76cfdf7914fde346e4d1163bcc854`.
- Process: exactly one `collect_c33_liquidation_events.py --enable-network` instance, PID `86852` at
  verification time.
- Output: `data/research/c33/events.jsonl`; historical import is false.
- First recorded epoch is `1788694536`, strictly after the activation and C-33 boundaries.
- The first two complete minutes contain all six exact closed one-minute candles plus public server
  heartbeats under one uninterrupted session. No liquidation snapshot had yet qualified for storage.

## Fail-Closed Activation Evidence

Three pre-activation attempts were retained under explicit `.failed-*` names and are excluded from
the active cohort. They exposed, respectively: same-second lifecycle versus strict boundary;
live Binance nesting of `ps`/`st` inside the order plus irrelevant all-market symbols; and the first
partial pre-activation candle. Each attempt stopped without accepting liquidation or candle outcome
data. Minimal guards were added and focused regressions pass before the fresh cohort was started.

## Verification

- Active ledger snapshot: 17 records — one STARTED lifecycle, four heartbeats, twelve closed klines,
  one session ID, unique keys, and zero pre-boundary rows.
- Thirteen focused collector tests pass.
- Full suite: 916 passed, one optional import-linter skip.

## Next Unit

TASK-0166 must add a deterministic read-only liveness/bucket auditor and monitor the active process.
It may not open the 30-day threshold warmup, calculate signals/outcomes, or change the frozen C-33
contract. Any process termination or integrity violation must keep buckets ineligible and be reported.
