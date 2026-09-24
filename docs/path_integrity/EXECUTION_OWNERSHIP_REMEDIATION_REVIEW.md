# P0 execution ownership — remediation gate

Source baseline: `88697f0`. Unit-1's six network-incapable tests proved two pre-broker service calls can arise from one logical intent; they did not prove two exchange orders. No production route was modified in this review.

## Original routes and registrations

1. `ArchitectureOrchestrator.__init__` and `start()` both call `SignalProcessor.setup_signal_processing`; it subscribes a lambda for `EXECUTION_INTENT` to `SignalProcessor._process_execution_intent`. `EventRouter.subscribe` appends without deduplication. This route immediately constructs an order and calls `execution_service.execute_order`.
2. `AutoDetectionOrchestrator.__init__` starts that architecture orchestrator, then subscribes `_handle_execution_intent_event`. It queues accepted intents; `_opportunity_processing_loop` calls `_execute_strategy_for_opportunity` and `_execute_trade_from_intent`, which independently constructs an order and calls `execution_service.execute_order`.

Both ultimately enter the configured execution service and its broker/LiveExecutionGuard path. These are independent pre-broker attempts, not a proven pair of broker sends.

## Responsibility difference blocking a removal-only patch

The auto-detection route supplies opportunity queueing, broker-active-order and pending-intent checks, a symbol lock, cooldown/health gate, stablecoin filter, heartbeat and liquidity guards, and order logging. It is the natural owner **if these opportunity-admission behaviors must remain canonical**. Its pending-intent check is conditional on `prevent_same_direction_trade_per_symbol` and is not, by itself, a durable logical-intent idempotency guarantee.

The direct SignalProcessor route uniquely performs `sanitize_sltp_levels` on the intent, rejects extreme SL/TP distances, and applies `MAX_ORDER_NOTIONAL_AMOUNT` before order construction. Its repeated registration can itself multiply executions. The auto-detection route currently takes `intent.stop_loss_price`/`take_profit_price` as supplied; merely deleting the direct route may remove the only observed source that attaches sanitized SL/TP to some intents. Broker-side SL/TP validation/enhancement is not equivalent evidence of preserved pre-broker semantics. Conversely, choosing the direct route and deleting the queue route would bypass its cooldown/opportunity-admission behavior. Both routes calculate dynamic size, heartbeat and liquidity independently; this is not a simple observation-only subscriber split.

## Decision required before implementation

Recommended ownership direction: auto-detection queue, because it is the existing opportunity-admission and execution orchestration route. But a safe implementation must first explicitly move/preserve direct-route-only SL/TP sanitization/distance rejection and notional cap, while defining a stable logical-intent idempotency claim that survives duplicate and concurrent delivery independent of the symbol duplicate-policy flag. It must also make `setup_signal_processing` idempotent for the event chain. This is more than removing one subscription and affects multiple safety semantics. Alternative: direct SignalProcessor ownership plus preservation of queue ranking/cooldown/admission; this has a larger behavior change. Neither route can be declared a semantics-preserving sole owner by a removal-only patch.

No selected authoritative owner has been activated. No production code/configuration, strategy, Fusion, risk, sizing, SL/TP, broker, or research cohort was changed. Therefore the requested post-remediation LONG/SHORT, duplicate, cooldown, risk-reject, concurrent, guard, and F01 regression claims cannot honestly be made. They remain mandatory for an approved implementation unit. Production, runtime and VST remain unverified/unremediated.

Final status: EXECUTION_OWNERSHIP_REQUIRES_ARCHITECTURAL_REVIEW
