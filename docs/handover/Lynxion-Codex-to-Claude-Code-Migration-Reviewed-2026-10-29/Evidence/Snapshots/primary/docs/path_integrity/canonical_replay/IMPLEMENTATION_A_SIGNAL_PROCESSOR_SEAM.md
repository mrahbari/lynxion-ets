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

## Authorized contract resolution (after `b95013d`)

The operator authorized an **optional explicit causal** `MarketObservation.market_price: Optional[float]`. The earlier price-source ambiguity is resolved by producer responsibility, not by interpreting `observation_value` or arbitrary metadata. The field was appended after existing fields so old positional/keyword constructors remain valid. `SignalProcessor` now forwards only a finite positive explicit value to a narrow recorder. Missing or invalid prices do not block analytical observation processing; invalid values and recorder failures are logged rather than silently swallowed. The former `observation.close` access and broad inner exception swallow were removed. A future replay composition can inject a local recorder. The default live adapter resolves the same risk-engine bridge registered by `bootstrap/lifecycle.py`; it does not create a second risk manager.

| Producer | Classification | Price decision |
|---|---|---|
| `TickWatcherAdapter` | EXPLICIT_CAUSAL_PRICE_AVAILABLE | The already-received latest tick has `price`; observation is constructed after reception. Populate only when finite/positive. |
| `HistoricalCandleWatcherAdapter` | AMBIGUOUS_PRICE_SEMANTICS | Stores a close and close-time-like timestamp, but `update_data` does not prove a completed bar for every caller; leave None. |
| `MarketPulseWatcher` (both observation paths) | AMBIGUOUS_PRICE_SEMANTICS | Latest candle exists, but completion/time alignment not proved; leave None. |
| `CMCScreener` | AMBIGUOUS_PRICE_SEMANTICS | Has a remote `price` field, but quote timestamp/price basis is not explicit; leave None. |
| `FundingRateWatcher`, `LiquidityWatcher`, `OrderFlowWSWatcher`, `TrendMTFWatcher`, `VolatilityWatcher`, `AnomalyMLWatcher` | NO_CAUSAL_PRICE | Observations encode analytical metrics, not a source-proven market price; leave None. |
| Fusion-created mock observation | NO_CAUSAL_PRICE | Reconstitutes interpreted signal for hierarchical classification; never a price source. |

`HistoricalClosedBarSource` itself enforces complete UTC bars and causal visibility, but does not currently construct `MarketObservation`; no candle-to-watcher price claim is made. A future historical producer may set price only after its completed-bar provenance is wired and tested. Price used by the risk manager is for rolling correlation; no sizing or risk rule was moved into the recorder. The sole other `record_price` caller found is the legacy backtester, not the canonical live observation path.

Focused source/contract/ownership/F01 regression: 64 passed, 0 failed. Four protected production persistence files had identical SHA-256 values immediately before and after the focused run. No broker client/order was constructed by new tests. Implementation A seam is VERIFIED for the scoped behavior; full replay, prefix invariance and live/replay parity are not.
