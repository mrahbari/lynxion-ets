# VST runtime verification — eligibility gate

Date: 2026-09-24 UTC. Scope: read-only eligibility assessment; no runner, broker connection, order, or configuration change.

## Verified baseline

- Repository HEAD: `87affd4`. No active Lynxion runner appeared in the inspected process list. Recent inspected logs were test output, not evidence of a post-remediation VST trade.
- Normal `./lynxion` launches `run_trading_system.py --mode production --auto-detect` after its duplicate-runner/cohort checks. It also supplies existing launcher environment values, including `LOG_LEVEL=WARNING` and maximum leverage 10; the latter differs from bare `load_settings()` value 5. No launcher or setting was changed.
- Read-only settings/preflight with launcher-effective leverage: `mode=TESTNET`, `ok=True`, zero blocking flags, `paper_trading=False`, `testnet=True`, `order_placement_enabled=True`, `live_trading=False`, primary/enabled broker BingX, BingX testnet enabled, credential fields present, `MAX_ORDER_NOTIONAL_AMOUNT=21.0`, `max_leverage=10.0`, fixed-position-size mode enabled. Presence and preflight do not establish credential validity, VST balance, exchange protections, or successful startup.
- Normal production construction is the CLI → lifecycle/container → auto-detection factory. Unit 3's network-incapable composition fixture observed one `ExecutionIntent` subscriber, the auto-detection queued owner, with in-process claim, sizing/order preparation, RiskEnforcement, and LiveExecutionGuard. This is **offline evidence**, not observation of a deployed process or BingX.
- Starting the normal process can instantiate network-capable adapters and authenticated BingX account reads (`BingXBrokerAdapter.connect()` obtains balance); natural market-data and broker traffic would follow. Therefore startup was not attempted during this gate. A naturally generated decision could in principle reach an order without altering trading semantics, but no time or trade frequency is assured.

## Requirement and observability assessment

| Required segment | Read-only finding | VST evidence status now |
|---|---|---|
| Normal startup; Watcher → Engine → Fusion → StrategyManager | Source/Unit-3 composition traces identify the intended route. No running process or natural event inspected. | UNKNOWN |
| ExecutionIntent; one auto-detection queue owner; atomic claim/cooldown/active-position veto | Unit-3 offline fixture exercises these. `ExecutionIntent.intent_id` exists and is used for the in-process claim, but successful claim/owner is not persisted with that ID. | NOT_OBSERVABLE as an end-to-end VST trace |
| Risk, sizing, SL/TP sanitization, notional/exposure/leverage controls, guard | Unit-3 offline fixture reaches core controls; current settings preserve them. Whether a future real process applies each control to a particular natural intent cannot be proved from a common persisted ID. | UNKNOWN per natural VST trade |
| Exactly one pre-broker attempt | Source ownership and offline duplicate tests support the invariant. Existing persistent records cannot count attempts by stable logical `intent_id`. | NOT_OBSERVABLE by logical intent |
| BingX VST submission, acknowledgement, protective orders, reconciliation, journal | Normal adapter/journal path exists. Its `client_order_id`/`order_ref` and exchange order ID can support downstream order-lifecycle inspection, but they are not deterministically linked to `ExecutionIntent.intent_id`. No post-`87affd4` VST order was observed. | UNKNOWN; downstream correlation alone is insufficient |

The identity gap is concrete: `ExecutionIntent.intent_id` is created in `domain/entities/order.py` and claimed in `infrastructure/orchestrators/_auto_detection_execution.py`; the final `Order` retains only an in-memory parent reference. `MultiBrokerExecutionService.execute_order()` creates its own client-order identity, and `live_order_journal.record_intent()` records order/client/broker references without the logical intent ID. The structured journal metadata extraction also omits it. Existing logs may contain incidental object text, but do not provide a guaranteed, durable join from natural signal through claim, pre-broker attempt, broker ID, protective orders, and reconciliation. Launcher `LOG_LEVEL=WARNING` further limits ordinary trace visibility. This is an observability finding, **not** proof of duplicate broker orders or a failed safety control.

## Decision and boundary

An unmodified natural VST trade could establish some downstream order facts, but cannot supply the specified direct, identity-linked evidence for sole ownership, one pre-broker attempt, and the complete post-`87affd4` path. No existing trustworthy post-`87affd4` runtime/VST evidence was found. This is therefore **not eligible for the requested end-to-end verification under current observability**, despite passing read-only configuration preflight. Lack of an active runner is not independently disqualifying.

Do not start Lynxion or force a signal to close the gap. A separate, reviewed observability change would need to carry the stable logical intent ID through the authoritative pre-broker record and broker/journal correlation, without changing trading decisions or controls; only then reassess eligibility for observing a future natural trade. This document does not authorize that change or any order. Broker timeout, unknown-result, and process-restart retry safety remain `BROKER_RETRY_SEMANTICS_UNRESOLVED`.

VST_RUNTIME_VERIFICATION_NOT_ELIGIBLE
