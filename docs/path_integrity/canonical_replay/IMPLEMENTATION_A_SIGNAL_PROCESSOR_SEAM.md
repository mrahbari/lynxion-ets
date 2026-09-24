# Implementation A — pre-edit architecture mismatch

Starting HEAD: `fdeaa7a`. Verdict: `IMPLEMENTATION_A_ARCHITECTURE_MISMATCH`. No production source/configuration was changed, and the price-recorder or forensic-sink seam was not implemented.

## Verified dependency trace

| Access | Source | Classification | Finding |
|---|---|---|---|
| Legacy `application.containers.container` → `risk_engine._risk_manager.record_price(...)` | `infrastructure/messaging/event_system.py`, `_process_observation`, lines 188–193 | DECISION_STATE | The target is bridged to the active bootstrap risk engine by `bootstrap/lifecycle.py` lines 26–27. But the passed price is `float(observation.close)`. |
| Global `forensic_logger` | same file, `_process_observation` and `_process_interpreted_signal`, lines 200 and 236 | OBSERVABILITY | Subscribed path imports the module-level logger; replay cannot currently scope its output. |
| Injected `event_router` | same file, constructor and subscriptions | ROUTING | Constructor accepts a router, though live module globals are created at lines 700–701. Existing subscription topology is unchanged. |
| Legacy direct `_process_execution_intent` container/logger lookups | same file, lines 334 and 638 | LEGACY / NOT SUBSCRIBED | Method is retained but the post-87affd4 `setup_signal_processing` does not subscribe it. Not part of this seam. |
| `update_market_data_heartbeat` wall clock fallback | same file | DECISION-TIME UNKNOWN | Separate replay clock/lifetime question; no change authorized in this unit. |

## Material contradiction and stop reason

`domain/entities/signal.py` defines `MarketObservation` with `symbol`, `observation_type`, `observation_value`, `confidence`, `timestamp`, and optional `metadata`; it has **no `close` field**. The inspected watcher constructors create this entity without adding `close`. Consequently, on the standard observation contract, `observation.close` raises `AttributeError`, which the broad `except Exception: pass` silently suppresses. The architecture review's statement that this path records the observation's market price cannot be treated as established behavior. The live container bridge identifies the intended risk instance, but does not make the price value valid.

Choosing `observation_value`, `metadata.latest_candle.close`, or another source would define new price semantics (including cases without a candle), not merely expose an existing dependency. Preserving the silent no-op would fail the requested T2 exact-price forwarding and leave the advertised seam misleading. Under the explicit pre-edit stop rule, neither choice was made.

## Review needed before Implementation A resumes

Specify the causal market-price contract for each observation type: which explicit field/metadata value is a tradable price, when it is available, and what happens when absent. Decide whether correcting the current swallowed recording failure is authorized as a separate behavior change. Then inject a narrow recorder targeting the same bridged live risk instance, plus a scoped forensic sink, and run T1–T11 with production-persistence hashes. No global replacement, broker connection, replay, or research result is justified by this finding.

The XMR blocker and causal status are unchanged: `XMR_ROOT_CAUSE_UNRESOLVED`. Full prefix invariance and live/replay parity remain `NOT_TESTABLE`.
