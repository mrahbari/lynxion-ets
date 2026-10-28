# Unit 3 — production/auto-detect composition trace (network-incapable)

Baseline: Unit-2 commit `5fc726c`. Scope: verify effective production-mode `--auto-detect` wiring and controls without constructing a network-capable broker, running `./lynxion`, starting watchers, or submitting a real/VST/paper order. This is execution correctness, not an edge test.

## Construction and subscriber graph

The actual CLI path is `run_trading_system.py --mode production --auto-detect` → `interface.cli.trading_system_production.main` → `bootstrap.lifecycle.lifespan` → `Container.resolve("auto_detection_orchestrator_factory")` → `Container._build_production_data_and_services` → `AutoDetectionOrchestrator`. Without `--auto-detect`, the CLI selects `ProductionTradingOrchestrator`; that is a distinct path and is not the tested ExecutionIntent owner here.

The production builder requests one execution service from `broker_registry` with `use_multi_broker=True`, primary `bingx`, builds a historical data provider, installs `build_vst_risk_enforcement()` into the process `live_execution_guard`, and wires paper-fill accounting. `AutoDetectionOrchestrator.__init__` starts `ArchitectureOrchestrator`, then subscribes `_handle_execution_intent_event`. `SignalProcessor.setup_signal_processing` now subscribes observation/interpreted/fused handlers once but no ExecutionIntent handler. `BrokerExecutionService` would normally dispatch via its multi-broker adapter and guard; in this unit the registry returned a no-network execution port. Reconciliation loops exist on the orchestrator but were not started in the fixture.

**Measured effective graph in the actual auto-detection factory with substituted ports:**

`EventRouter.EXECUTION_INTENT (1 subscriber)` → `AutoDetectionOrchestrator._handle_execution_intent_event` → opportunity queue → `_execute_trade_from_intent` → sanitized/capped `Order` → injected execution port → real `LiveExecutionGuard` + real `RiskEnforcement` → **memory-only callback**. The broker adapter and its actual network send were deliberately absent. A memory-only ledger replaced the persistent order ledger for this test.

The no-network fixture replaced broker registry outputs, market data provider, watcher construction, and paper fill engine *before* the production factory was resolved. It did not invoke `RunAutoDetectionUseCase.run`, `initialize_system`, watcher monitoring, `./lynxion`, or an authenticated broker. It used the actual `Container._build_production_data_and_services`, auto-detection constructor, event router, risk-enforcement builder and guard code. Thus this is an **offline composition-runtime verification**, not verification of any already-running process.

Current settings read through `load_settings()` (values only; no secrets): paper trading `False`, testnet `True`, default broker `bingx`, configured maximum order notional `21.0` USDT, configured max leverage `5.0`, fixed-position-size flag `True`, same-direction duplicate prevention `True`. These were not changed. The test's risk-engine sizing output was injected to isolate order propagation; it does **not** prove that the current fixed-size setting selects dynamic sizing in production.

## Deterministic traces

`tests/unit/test_path_integrity_unit3_runtime_wiring.py` uses a unique `intent_id` per fixture and checks actual registered subscriber identity. Both sides were tested for every row below. A “dispatch” is a local memory-only callback after `LiveExecutionGuard`; it is **not** a broker request.

| Scenario | Queue / pre-broker result | Guard / memory dispatch |
|---|---|---|
| Normal LONG / SHORT | One subscriber, one queue item, one claimed intent, one order | Real RiskEnforcement and guard allow; one memory callback |
| Duplicate event delivery | Two queue items in the deliberately permissive queue fixture; same `intent_id` claimed once | One order/guard decision/callback |
| Concurrent duplicate execution | Two simultaneous calls for one `intent_id`; one claim wins | One order/guard decision/callback |
| Cooldown block | Queue accepted, execution-side cooldown veto | Zero orders/guard calls/dispatches |
| Risk rejection | `is_trading_allowed` forced false on the real fixture RiskEnforcement instance | One pre-broker order, guard denies, zero dispatches |
| Wrong-side raw SL/TP | Existing sanitizer produces valid side-relative levels before order | One guarded callback; no wrong-side level survives |
| Notional cap | Fixture env cap 5 USDT, price 100, quantity clipped to 0.05 | One guarded callback |
| Active order | Fake broker reports an active order at admission | No queue item, no pre-broker order/dispatch |
| Guard rejection | Local guard kill switch engaged | One pre-broker order, zero dispatches |
| Two independent intents, inverse sizing | Injected risk sizing 0.1 then 0.05 for wider stop | Two distinct IDs/orders/callbacks; final quantities preserved |

The risk and guard tests demonstrate *zero broker dispatch*, not zero calls to the pre-broker execution service. The actual `BrokerExecutionService` is not invoked here, so its adapter-specific protection and journal behavior are supported only by separate unit tests/source trace, not this composed fixture.

## Control-preservation result and limits

The composed path reached queue admission, active-order veto, cooldown, atomic in-process claim, risk-engine sizing call, `sanitize_sltp_levels`, optional `MAX_ORDER_NOTIONAL_AMOUNT`, `Order` construction, real `RiskEnforcement`, and real `LiveExecutionGuard`. Distinct prior tests cover exposure/position limits, heartbeat, and reconciliation in isolation. The network-incapable port cannot prove the live multi-broker adapter, exchange minimum/maximum lot constraints, reconciliation against actual open orders, persistent ledger output, or a deployed process's exact subscriber inventory. `Container._build_production_data_and_services` catches and suppresses exceptions in risk/paper wiring; successful fixture construction proves the normal branch, not that every real startup did so. A real runtime should fail closed or be independently checked if risk wiring is absent; no production code change is authorized in Unit 3.

**In-process duplicate protection:** VERIFIED for the exercised auto-detect composition and same logical `intent_id` within this test process. **Process-restart idempotency:** NOT VERIFIED. **Broker timeout / unknown-result resolution:** NOT VERIFIED. **Actual VST order path:** NOT VERIFIED. No automatic retry may be inferred from these tests; after unknown broker result, read-only reconciliation by stable broker order identity remains the unresolved boundary. No exchange-level exactly-once claim is made.

## Verification record

`pytest -q tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_f01_offline_intent_sizing.py tests/unit/test_risk_enforcement.py tests/unit/test_live_execution_guard.py tests/unit/test_r1_reconcile_integration.py tests/unit/test_symbol_cooldown_gate.py tests/unit/test_heartbeat_guard_remediation.py tests/unit/test_portfolio_capacity_guard.py --disable-warnings --tb=short`: **110 passed**, 26 warnings. No broker/network-capable execution port was present.

Status: `SOURCE_REMEDIATED=YES`; `TEST_VERIFIED=YES`; `OFFLINE_COMPOSITION_RUNTIME_VERIFIED=YES`; `DEPLOYED_RUNTIME_VERIFIED=NO`; `VST_VERIFIED=NO`.

خلاصهٔ فارسی: در ساخت آزمایشیِ همان مسیر production/auto-detect، فقط یک مالک سفارش ثبت شد و کنترل ریسک و guard واقعاً فراخوانی شدند. همهٔ «ارسالها» فقط callback داخل حافظه بودند. این نتیجه نسخهٔ در حال اجرا یا رفتار صرافی را تأیید نمی‌کند؛ بازیابی امن پس از timeout یا restart نیز هنوز حل نشده است.
