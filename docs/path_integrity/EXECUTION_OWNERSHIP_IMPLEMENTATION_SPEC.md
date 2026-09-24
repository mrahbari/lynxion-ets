# P0 — Single execution ownership: architectural review and implementation specification

Scope: design only. Source baseline `ab23e74`; Unit-1 trace `88697f0`. No route, broker, configuration, strategy, or research cohort is changed here. Target guarantee is **at most one authoritative pre-broker attempt per logical intent inside one controlled Lynxion process**. It is not an exactly-once exchange-fill guarantee.

## 1. Verified paths and responsibility matrix

`ArchitectureOrchestrator.__init__` **and** `start()` call `SignalProcessor.setup_signal_processing`, which appends an `EXECUTION_INTENT` handler in `infrastructure/messaging/event_system.py`. That handler directly constructs and executes an order. `AutoDetectionOrchestrator.__init__` starts the architecture orchestrator, then appends its own `EXECUTION_INTENT` handler. That handler admits/queues the intent; `_opportunity_processing_loop` calls `_execute_strategy_for_opportunity` → `_execute_trade_from_intent` → constructs and executes a second order. `EventRouter.subscribe` does not deduplicate handlers. Unit-1's offline fixture proved two service calls for one intent, not two broker sends.

Classification describes *observed responsibility*, not an assertion that either implementation is sufficient by itself. `BOTH_DIFFERENT` requires parity review before one implementation is removed.

| Responsibility | Classification | Source / distinction |
|---|---|---|
| Opportunity admission and ranking | QUEUE_ONLY | `AutoDetectionOrchestrator._handle_execution_intent_event`/queue processing; direct handler executes immediately. |
| Queueing, symbol processing lock | QUEUE_ONLY | `AutoDetectionOrchestrator` queue and `_get_symbol_lock`. |
| Symbol cooldown | BOTH_DIFFERENT | Auto route checks `symbol_cooldown_gate` before order; shared `RiskEnforcement.enforce` also checks cooldown at guard. Direct route has no equivalent early admission check. |
| Same-symbol duplicate / active position protection | BOTH_DIFFERENT | Auto pending-intent and broker-active-order checks are conditional; `BrokerExecutionService.execute_order` checks active positions/pending orders when configured. Neither is stable logical-intent deduplication. |
| Dynamic sizing and fixed-sizing fallback | BOTH_DIFFERENT | Both call `risk_engine.calculate_dynamic_size` and have separate fallback/order construction; F01 characterized the direct route only. Actual configured fixed-mode wiring must be held constant and verified for the chosen route. |
| Exposure / `MAX_POSITION_EXPOSURE` | DOWNSTREAM_SHARED | `EnterpriseRiskManager` sizing/validation and `RiskEnforcement` at `LiveExecutionGuard`; hard VST exposure limits are in `infrastructure/risk/risk_enforcement.py`. Pre-broker quantities may differ between routes. |
| `MAX_ORDER_NOTIONAL_AMOUNT` | DIRECT_ONLY | `SignalProcessor._process_execution_intent` applies settings/env cap. No corresponding cap found in `_auto_detection_execution.py`; downstream hard VST limit is a different control. |
| Leverage constraint | BOTH_DIFFERENT | Both set `requested_leverage` from settings, but each builds its own `Order`; broker/guard validation remains shared. Verify normalized output before removing either route. |
| Minimum/maximum quantity | BOTH_DIFFERENT | Both floor calculated quantity at 0.001 and clip to observed depth; `EnterpriseRiskManager` caps exposure. No general exchange-specific maximum quantity proven at this boundary. A floor can increase risk above a tiny calculated size. |
| SL/TP source and sanitation | BOTH_DIFFERENT | Direct route uses `sanitize_sltp_levels`, attaches `Money` values to the intent, and rejects >50% distances. Auto route takes intent attributes as-is. `BrokerExecutionService` may enhance missing values and validates final order, but this is not the same preparation policy. |
| Wrong-side SL/TP rejection | DOWNSTREAM_SHARED | `RiskEnforcement` and `BrokerExecutionService._validate_order_parameters_before_broker` reject invalid sides; direct route may sanitize first, changing the attempted value. |
| Order construction | BOTH_DIFFERENT | Two separate `Order(...)` blocks with potentially different quantity and SL/TP. |
| LiveExecutionGuard and broker dispatch | DOWNSTREAM_SHARED | Configured execution service is called by either route; `BrokerExecutionService`/multi-broker path enters guard and broker adapter. Unit-1 spy did not invoke these. |
| Reconciliation and journal/persistence | DOWNSTREAM_SHARED / UNKNOWN | Execution service and guard write order/trade evidence; orchestrator has reconciliation cadence. Exact equivalence of route-specific decision logs and all restart states is not proven. |
| Failure/retry | BOTH_DIFFERENT / UNKNOWN | Auto route clears pending intents on many failures; direct handler returns without queue state. Broker timeout/unknown-result and crash recovery lack a proven logical-intent lifecycle. |

## 2. Ownership decision and minimal architecture

**Recommended owner: the existing auto-detection queue**, because it already controls opportunity admission, queue ordering, symbol locking, cooldown and execution lifecycle. Direct `SignalProcessor` may continue observation/heartbeat processing but must not construct or submit an order. Ensure registration of the remaining event handlers is idempotent across `ArchitectureOrchestrator.__init__`/`start()`; a repeated subscription must not multiply a decision or execution callback. Do not add a third route.

The owner must call **one** authoritative pre-broker preparation/policy function before its existing execution service. Reuse the current `sanitize_sltp_levels` utility and risk engine rather than copy the direct handler's whole order path. Retain the currently configured numeric policies, including optional `MAX_ORDER_NOTIONAL_AMOUNT`, exposure, leverage, SL/TP and minimum quantity. `RiskEnforcement` at the guard remains final risk authority; pre-broker preparation cannot expand a rejected size or weaken a gate. Strategy supplies intent; Fusion does not set risk policy; broker only dispatches an already-approved order. If final broker enhancement changes SL/TP or quantity, revalidation by Risk/guard remains mandatory.

Implementation should be staged under a *separate approval*: (1) characterize route-specific normalized `Order` outputs and vetoes with no-network fixtures; (2) move only direct-only preparation controls into one existing owner-invoked policy function; (3) remove direct route's execution subscription and make processor setup idempotent; (4) prove exactly-one pre-broker attempt and all vetoes. Do not remove old code until parity tests show no required safety behavior was lost. No strategy/Fusion/risk threshold changes.

## 3. Logical intent identity and lifecycle

The current `SignalEvent.correlation_id` is supplied by the aggregator using symbol plus current timestamp; it is event correlation, not a demonstrated stable intent ID. Python object identity is process-local and unsuitable after restart. Specify a newly created opaque `intent_id` **once at ExecutionIntent creation**, then carry it unchanged in event, queue, pre-broker order metadata, decision ledger and, where adapter support is verified, deterministic client-order ID. Do not derive it from symbol/side/time because distinct valid intents may collide. ID creation must precede publication; redelivery/retry must reuse the same ID. A persisted unique claim (or equivalent atomic journal transaction) must be independent of `prevent_same_direction_trade_per_symbol`.

States: `CREATED` → `QUEUED` → `CLAIMED` → `PREBROKER_REJECTED` or `SUBMISSION_IN_FLIGHT` → `BROKER_ACCEPTED` / `BROKER_REJECTED` / `UNKNOWN_RESULT`. Claim transition must be atomic under concurrency **before** order construction; same-ID duplicate deliveries observe the existing state and never create a second pre-broker attempt. Terminal rejections remain auditable. A retry after a known pre-broker rejection requires an explicit *new* decision/intent ID if conditions change. Never automatically retry a submitted/unknown-result ID: first reconcile by a verified exchange client-order ID or order history. If the broker/adapter cannot query and deduplicate by such an ID, `UNKNOWN_RESULT` must stop automatic send and require reconciliation/operator review. Persisting only in process memory cannot cover restart; exact journal durability and broker idempotency support are **UNKNOWN pending adapter verification**. This boundary must be resolved before claiming restart-safe idempotency.

## 4. Required failure semantics

| Condition | Required behavior |
|---|---|
| Risk or cooldown rejection; invalid SL/TP | Zero broker attempts; record reason; terminal for that ID. |
| Notional cap | Apply existing configured cap before final risk/guard check; reject if clipped quantity violates minimum/exchange constraints; no numerical-policy change. |
| Duplicate event/queue redelivery/concurrent delivery | One atomic claim wins; others make zero pre-broker attempts, regardless of symbol duplicate-policy setting. |
| Active position/order | Preserve existing broker/pending checks and authoritative risk denial; zero send when conflict is known. |
| Guard rejection | Zero broker send; record guard reason; no silent alternative route. |
| Broker explicit rejection | Record terminal rejection; any later new market decision must use a new ID. |
| Broker timeout/unknown result | Do not resend until read-only reconciliation proves no accepted order; if proof unavailable, `UNKNOWN_RESULT` and operator review. |
| Restart between acceptance and result | Recover journal/claim state, reconcile before any resend. Whether current broker adapters can supply sufficient client-order lookup is UNKNOWN. |

Do not equate one pre-broker attempt with one exchange execution; network uncertainty and venue idempotency remain separate.

## 5. Acceptance and test contract for a later implementation

- Preserve F01: same equity/risk budget, both LONG and SHORT, larger valid stop distance gives smaller dynamic quantity when no cap/floor dominates; compare final pre-broker `Order` to calculation. Verify fixed mode, `MAX_POSITION_EXPOSURE`, `MAX_ORDER_NOTIONAL_AMOUNT`, leverage and min/max constraints separately.
- Preserve normalized order output and veto reasons for the selected canonical route where policies are equivalent; explicitly test direct-only SL/TP sanitation and optional notional cap after transfer.
- Network-incapable fixture: normal LONG/SHORT one pre-broker call; duplicate delivery and simultaneous delivery at most one; cooldown, risk, wrong-side SL/TP and active-position veto zero; guard invocation/denial and broker-dispatch spy; no real/VST orders.
- Verify one subscriber registration over init/start/restart lifecycle; queue opportunity ordering and logging/reconciliation hooks remain observable.
- Fault-injection: broker explicit reject, timeout, unknown result, and crash/restart between claim and result; no automatic duplicate submission. Any unproven restart case is a release blocker, not a passing test.
- Do not claim `SOURCE_REMEDIATED`, `TEST_VERIFIED`, `RUNTIME_VERIFIED` or `LIVE/VST_VERIFIED` from this design document. All remain false at this point.

## 6. Expected change surface and unresolved gate

Likely files for a later reviewed implementation: `infrastructure/messaging/event_system.py`, `infrastructure/orchestrators/architecture_orchestrator.py`, `infrastructure/orchestrators/auto_detection_orchestrator.py`, `infrastructure/orchestrators/_auto_detection_execution.py`, the `ExecutionIntent` entity/creation site, and focused tests. A small persistent claim/journal adapter may be required **only after** its durability and broker reconciliation contract are specified. Existing `shared.utils.sanitize_sltp_levels`, risk engine, `RiskEnforcement`, `LiveExecutionGuard`, execution service and broker adapters should be reused, not reimplemented. Exact LOC and persistence format remain UNKNOWN until adapter reconciliation is verified. No production implementation or runtime verification is authorized by this document.

**Decision for implementation review:** approve the queued-route ownership *direction* only with explicit preservation of direct-only policy controls and a resolved durable ID/reconciliation contract. Do not interpret this as approval to deploy or place an order.
