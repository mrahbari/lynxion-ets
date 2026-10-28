# Execution Truth Ledger (ETL)

**Date:** 2026-06-12
**Module:** `shared/execution_truth_ledger.py` (singleton `execution_truth_ledger`)
**Purpose:** An immutable, append-only, per-order audit trail that records — for **every** order that
reaches the execution-safety boundary — the exact flags, guard decision, runtime states, route, and
broker outcome. It is written **before** any send is attempted and **cannot be bypassed** by any
execution path.

---

## 1. Guarantees

| Requirement | How it is met |
|---|---|
| **Immutable / append-only** | Records are only appended (open in `"a"` mode, per-record). Nothing is ever updated or deleted. |
| **Tamper-evident** | Each record carries `prev_hash` + a SHA-256 `hash` over `prev_hash + canonical(record)`. Any edit to a past record breaks the chain; `verify()` reports `ok:false` and the `seq` where it broke. |
| **Written BEFORE send** | The guard's `authorize_and_send` writes the `decision` record (flags + trace + states + route) **before** `send_fn` (the real `place_order`) is ever invoked — and the write is `flush()`+`fsync()`'d. |
| **Cannot be bypassed** | The only authorized send path is `LIVE_EXECUTION_GUARD.authorize_and_send`, and both real send-points route through it. The decision record is written unconditionally there — including for `BLOCKED` orders. |
| **Durable** | Each append is flushed and `fsync`'d before the caller proceeds to the send. |
| **Crash-safe ordering** | Append-only + per-record open means a crash can never truncate prior records; on restart a new `ExecutionTruthLedger` resumes the `seq` counter and hash chain from the file's tail. |

Storage: newline-delimited JSON (JSONL) at `logs/execution_truth_ledger.jsonl` (override with
`EXECUTION_TRUTH_LEDGER_PATH`). Standard-library only; thread-safe via an internal lock.

---

## 2. Record schema

Each **order** produces a `decision` record (always, pre-send) and, when there is an outcome, a linked
`result` record (joined by `order_ref`).

### Common envelope (every record)
| Field | Meaning |
|---|---|
| `seq` | Monotonic sequence number |
| `ts` | UTC ISO-8601 timestamp |
| `event` | `"decision"` or `"result"` |
| `prev_hash` / `hash` | SHA-256 chain (tamper-evidence) |
| `order_ref` | Opaque id linking an order's decision ↔ result |
| `symbol`, `broker` | Order symbol and target broker |
| `route` | `PAPER` / `TESTNET` / `LIVE` / `BLOCKED` |

### `decision` record (written before send)
| Field | Meaning |
|---|---|
| `decision_trace` | `{rule, reason}` — which precedence rule decided and why |
| `input_flags` | The **exact** values the decision used: `paper_trading`, `testnet_resolved`, `global_testnet`, `order_placement_enabled`, `live_trading_env` |
| `kill_switch` | `{engaged, reason, since}` |
| `circuit_breaker` | Full per-broker breaker status (`state`, `failure_count`, `should_reset`, …) |
| `risk_engine` | Risk-engine state snapshot if a provider is registered; otherwise `{"status":"not_wired_into_order_path"}` (honest — the portfolio risk engine is not yet on the order path; see the Phase-9 audit) |

### `result` record (after the send attempt / simulation)
| Field | Meaning |
|---|---|
| `order_id` | Broker order id, or the `PAPER-…` simulated id |
| `broker_response` | The broker's response (or `EXCEPTION: …`), `null` for paper |
| `sent_to_exchange` | `true` only when a real send occurred (the ground truth for "did it leave?") |
| `execution_latency_ms` | Wall-clock latency of the send |
| `success` | Whether a valid order id was returned |

---

## 3. Real sample (a LIVE order)

```json
{ "seq": 1, "event": "decision", "prev_hash": "000…000",
  "order_ref": "49353bda…", "symbol": "BTC/USDT", "broker": "bingx", "route": "LIVE",
  "decision_trace": { "rule": "6:live_authorized", "reason": "LIVE trading authorized (LIVE_TRADING=true)" },
  "input_flags": { "paper_trading": false, "testnet_resolved": false, "global_testnet": false,
                   "order_placement_enabled": true, "live_trading_env": true },
  "kill_switch": { "engaged": false, "reason": null, "since": null },
  "circuit_breaker": { "name": "order_path:bingx", "state": "closed", "failure_count": 0,
                       "failure_threshold": 5, "should_reset": false, "timeout": 60 },
  "risk_engine": { "status": "not_wired_into_order_path" },
  "hash": "0126e1ad…" }

{ "seq": 2, "event": "result", "prev_hash": "0126e1ad…",
  "order_ref": "49353bda…", "symbol": "BTC/USDT", "broker": "bingx", "route": "LIVE",
  "order_id": "8a1f-exch-order-id", "broker_response": "8a1f-exch-order-id",
  "sent_to_exchange": true, "execution_latency_ms": 0.002, "success": true,
  "hash": "deba341d…" }
```

A `BLOCKED` order produces only the `decision` record (no send); a `PAPER` order produces a
`decision` plus a `result` with `sent_to_exchange:false` and a `PAPER-…` id.

---

## 4. Integration (single chokepoint, before send)

```
LIVE_EXECUTION_GUARD.authorize_and_send(broker, settings, order, send_fn):
    with guard lock:
        decision = evaluate(...)                 # atomic snapshot of all flags
        ledger.append("decision", {...})         # ← WRITTEN BEFORE SEND, always
        if BLOCKED:  return decision, None        # decision record stands as the audit
        if PAPER:    ledger.append("result", sim) ; return decision, sim_id   # no send
        order_id = send_fn()                      # the ONLY real place_order, under the lock
        ledger.append("result", {broker_response, latency, sent_to_exchange:true, ...})
        return decision, order_id
```

Because `authorize_and_send` is the sole authorized send path and the decision write precedes
`send_fn`, **no order can be sent without first being recorded**, and no execution path can bypass the
ledger.

---

## 5. API

| Method | Use |
|---|---|
| `append(event, payload) -> record` | Append one chained record (used by the guard). |
| `new_order_ref() -> str` | Mint an id linking a decision to its result. |
| `verify() -> {ok, records, broken_at}` | Re-read and validate the hash chain (tamper detection). |
| `read_all() -> [record]` | Load all records (analysis / reconciliation). |

Operational note: a follow-on improvement is to surface `verify()` and recent records on the
monitoring dashboard, and to feed the ledger into the (still-missing) broker↔local reconciliation
loop identified in the Phase-9 audit.

---

## 6. Verification

`tests/unit/test_execution_truth_ledger.py` (8 tests, all passing) covers: hash chaining; tamper
detection; seq/chain resume across instances; decision-written-before-send; blocked orders still
audited (cannot be bypassed); paper records without send; recorded flags == exact decision inputs;
and the concurrency invariant (no send while killed/breaker-open; every LIVE send recorded under an
allowed snapshot; chain intact) under 720 concurrent chaotic orders.

```
.venv/bin/python -m pytest tests/unit/test_execution_truth_ledger.py -q   # 8 passed
```
