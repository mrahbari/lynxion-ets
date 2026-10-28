# LIVE_EXECUTION_GUARD — End-to-End Validation Matrix

**Date:** 2026-06-12
**Subject:** `shared/live_execution_guard.py` enforced in the live order path.
**Goal:** Prove, on the actual runtime path, that the guard yields the required decision for each
flag combination — and, decisively, whether a real order is sent to the exchange.

**Result:** ✅ **6/6 scenarios match expectations.** Safe to commit.

---

## 1. Method (this is the real path, not a mock of it)

The harness drives the **real** `MultiBrokerExecutionService.execute_order(order)` — the wired
production send-point — so the genuine guard integration and the genuine service log lines execute.
To isolate the guard decision from unrelated layers and avoid touching real exchanges:

- The concrete broker is a **`FakeBroker`** injected into `svc.brokers['bingx']`; its `place_order`
  increments a counter and returns a synthetic id. **The counter is the ground truth for "did a real
  order leave the system?"** (0 = nothing sent; ≥1 = a send actually occurred).
- Unrelated pre-broker layers (symbol approval, duplicate prevention, SL/TP enhancement, parameter
  validation, notifications) are neutralized so each scenario exercises exactly the guard branch.
- Flags are supplied through the same fields the runtime reads: `settings.broker.paper_trading`,
  `settings.broker.bingx_testnet` (per-broker override of `BROKER_TESTNET`),
  `settings.broker.bingx_order_placement_enabled`, and the `LIVE_TRADING` environment variable.
- Logs are captured at the **root logger** (the project's `EnhancedLogger` uses stdlib `logging` and
  propagates), so the lines below are the real runtime emissions.

Interpretation of the guard's four modes: `PAPER` = simulated, never sent · `TESTNET` = sent to the
testnet endpoint · `LIVE` = sent to the live endpoint · `BLOCKED` = rejected, never sent.

> Note: a `kill switch DISENGAGED` WARNING appears at the top of every scenario — that is the harness
> resetting runtime state between scenarios, not part of the order path.

---

## 2. Results matrix

| # | `paper_trading` | `BROKER_TESTNET` | `LIVE_TRADING` | Other | Expected | **Actual mode** | Real sends | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | true  | true  | false | — | PAPER   | **PAPER**   | 0 | ✅ |
| 2 | false | true  | false | — | TESTNET | **TESTNET** | 1 | ✅ |
| 3 | false | false | false | — | BLOCKED | **BLOCKED** | 0 | ✅ |
| 4 | false | false | true  | — | LIVE    | **LIVE**    | 1 | ✅ |
| 5 | false | false | true  | kill_switch=ENGAGED | BLOCKED | **BLOCKED** | 0 | ✅ |
| 6 | false | false | true  | circuit_breaker=OPEN | BLOCKED | **BLOCKED** | 0 | ✅ |

Scenarios 5 and 6 use the otherwise-LIVE configuration (`paper=false, testnet=false,
LIVE_TRADING=true`, placement enabled) to prove the kill switch and circuit breaker override **all**
other flags.

---

## 3. Demonstrated runtime path (captured logs)

### Scenario 1 — `paper_trading=true`, `BROKER_TESTNET=true`, `LIVE_TRADING=false` → **PAPER**
```
[WARNING] 🧪 PAPER MODE — order SIMULATED on BINGX (NOT sent to exchange): PAPER-BINGX-BTCUSDT-000001 [paper_trading enabled — order simulated, not sent]
-> returned order id: 'PAPER-BINGX-BTCUSDT-000001'   real send to exchange: 0 call(s)
```
`paper_trading` is the absolute override: no order is sent even though testnet is on.

### Scenario 2 — `paper_trading=false`, `BROKER_TESTNET=true`, `LIVE_TRADING=false` → **TESTNET**
```
[INFO] 🔐 LIVE_EXECUTION_GUARD authorized TESTNET send on BINGX: sending to bingx TESTNET endpoint
[INFO] ✅ ORDER PLACED SUCCESSFULLY ON BINGX: EXCH-ORDER-0001
-> returned order id: 'EXCH-ORDER-0001'   real send to exchange: 1 call(s)
```
Testnet routing is preserved and works **without** `LIVE_TRADING` — `BROKER_TESTNET` selects the
endpoint and the order is sent to testnet.

### Scenario 3 — `paper_trading=false`, `BROKER_TESTNET=false`, `LIVE_TRADING=false` → **BLOCKED**
```
[ERROR] 🛑 LIVE_EXECUTION_GUARD BLOCKED order on BINGX: live endpoint requires explicit LIVE_TRADING=true — accidental live execution prevented
-> returned order id: None   real send to exchange: 0 call(s)
```
The accidental-live case: live endpoint with no explicit opt-in is blocked. Nothing is sent.

### Scenario 4 — `paper_trading=false`, `BROKER_TESTNET=false`, `LIVE_TRADING=true` → **LIVE**
```
[INFO] 🔐 LIVE_EXECUTION_GUARD authorized LIVE send on BINGX: LIVE trading authorized (LIVE_TRADING=true)
[INFO] ✅ ORDER PLACED SUCCESSFULLY ON BINGX: EXCH-ORDER-0001
-> returned order id: 'EXCH-ORDER-0001'   real send to exchange: 1 call(s)
```
Deliberate live trading: only the explicit `LIVE_TRADING=true` opt-in permits a live send.

### Scenario 5 — kill switch ENGAGED (all other flags green for LIVE) → **BLOCKED**
```
[CRITICAL] LIVE_EXECUTION_GUARD kill switch ENGAGED: operator emergency stop
[ERROR]    🛑 LIVE_EXECUTION_GUARD BLOCKED order on BINGX: kill switch engaged: operator emergency stop
-> returned order id: None   real send to exchange: 0 call(s)
```
Kill switch has highest precedence: even with `LIVE_TRADING=true` and a live endpoint, nothing is
sent.

### Scenario 6 — circuit breaker OPEN (all other flags green for LIVE) → **BLOCKED**
```
[ERROR] 🛑 LIVE_EXECUTION_GUARD BLOCKED order on BINGX: circuit breaker OPEN for bingx (failures=5)
-> returned order id: None   real send to exchange: 0 call(s)
```
The per-broker breaker (`order_path:bingx`) was tripped to OPEN by repeated send failures; while OPEN
it blocks all sends regardless of the other flags.

---

## 4. `.env` key-casing integrity (requested check)

The runtime sources these flags from **uppercase** environment keys (verified in
`application/configs/_config_extractors.py`):

| Setting field | Environment key |
|---|---|
| `broker.paper_trading` | `BROKER_PAPER_TRADING` |
| `broker.testnet` | `BROKER_TESTNET` |
| `broker.bingx_testnet` | `BINGX_TESTNET` (and `BINANCE_/MEXC_/PHEMEX_TESTNET`) |
| `broker.bingx_order_placement_enabled` | `BINGX_ORDER_PLACEMENT_ENABLED` (etc.) |
| guard live opt-in | `LIVE_TRADING` |

A scan of the working `.env` found **no** `paper_trading`/`BROKER_PAPER_TRADING` (or testnet) key
present, so there is no lowercase entry to normalize — the canonical keys are already uppercase and
the `.env` (gitignored, secret-bearing) was left untouched to preserve its integrity. If a
`paper_trading` line is ever added to `.env`, it must use the uppercase canonical key
`BROKER_PAPER_TRADING=true|false`; a lowercase `paper_trading=…` line would be ignored by the loader
(no effect) and should be avoided.

---

## 5. Conclusion

Every required scenario produced the expected decision **and** the correct real-send behaviour
(0 sends for PAPER/BLOCKED, 1 send for TESTNET/LIVE), demonstrated on the actual
`execute_order` runtime path with captured logs. The kill switch and circuit breaker override all
flags. Accidental live execution is impossible without an explicit `LIVE_TRADING=true`, and testnet
functionality is fully preserved.

**Validation status: PASS — ready to commit.** (Reproduce with
`.venv/bin/python -m pytest tests/unit/test_live_execution_guard.py -q` for the unit matrix, 11/11.)
