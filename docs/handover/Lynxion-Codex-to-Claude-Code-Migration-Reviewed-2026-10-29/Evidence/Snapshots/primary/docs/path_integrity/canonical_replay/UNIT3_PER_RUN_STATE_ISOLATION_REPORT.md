# Unit 3 — per-run isolation architectural stop

Starting commit `8016007`. This is a **read-only dependency investigation**, not a replay implementation. The explicit architectural stop condition applies: a full canonical context would still resolve live/global risk and persistence, and removing that coupling safely spans the event processor, Fusion, StrategyManager/adapters, auto-detection execution and risk/journal ports. No global state was cleared, no production source/config was changed, and no replay context was constructed or claimed isolated.

## Actual dependency graph and first unsafe boundaries

`MarketObservation` → `SignalProcessor._process_observation` → `EngineService.process_observation` → `SignalProcessor._process_interpreted_signal` → `FusionService.fuse_signals([signal])` → `SignalAggregator._collect_fused_signal/_perform_aggregation` → `StrategyManager.evaluate_fused_signal` → `ExecutionIntent` → `AutoDetectionOrchestrator` queued owner → `_AutoDetectionExecutionMixin._execute_trade_from_intent` → Risk/guard/execution service.

The first unsafe read is inside `_process_observation`: `application.containers.container` is imported and `container.resolve("risk_engine")` records a price into its mutable portfolio manager. The same processor imports the global forensic logger. The global `event_router` starts a thread on module import, and `signal_aggregator` subscribes to it; Unit 2 provides injectable aggregator/router seams but the production `AutoDetectionOrchestrator` explicitly imports global engine/Fusion/strategy/router and starts the global `ArchitectureOrchestrator`.

`FusionService.__init__` binds `hierarchical_fusion_service`, a module singleton with `symbol_manager` and per-symbol regime/direction/execution dictionaries. The underlying symbol state machine records wall-clock transition times. `StrategyManager()` can create fresh adapters, but each `BaseStrategyAdapter` owns buffers, positions, per-symbol intent/cooldown/daily counters and other mutable dictionaries. The aggregator's Unit-2 injected selector does not by itself isolate a real StrategyManager or its adapters.

The authoritative queued execution route uses a class-level `_claimed_intent_ids` set/lock, global `symbol_cooldown_gate`, global container risk engine, shared pending-order tracker, broker active-order checks and order/reconciliation journals. `RiskEnforcement` loads/saves `data/sl_cooldown_journal.json` by fixed module path even when otherwise constructed with a fresh manager. `SymbolCooldownGate` is a singleton that reads cooldown/trade journals at construction and writes cooldown state. A nominally fresh replay risk instance could therefore touch production persistence. A network-incapable broker alone does not solve that.

## Smallest reviewable seams — not implemented

1. Pass a per-run service scope to `SignalProcessor` for price recording and forensic output; retain live defaults through the production composition root, but forbid global container lookup in replay. Do not use a global swap/monkeypatch.
2. Make `FusionService` accept a per-run `HierarchicalFusionService` and event clock; construct its symbol manager fresh. Keep algorithms/weights unchanged. Audit whether the singleton logger writes state before replay use.
3. Construct a fresh `StrategyManager` with fresh adapters and explicitly scoped configuration; inject it into the already-injectable aggregator. Audit adapter time reads and any nested shared services before declaring isolation.
4. Make intent claims instance-scoped for an isolated owner; inject cooldown/position/pending-order and risk ports, backed by in-memory replay implementations with the **same policy**. The live owner keeps its existing adapters. RiskEnforcement's fixed-path journal dependency must become an explicit persistence port or otherwise be proven unreachable in replay.
5. Compose a fresh router without starting global background threads, a deterministic clock and a hard network-incapable execution port. Then test two contexts, two symbols, hash production persistence before/after and compare repeated traces. This is a later reviewed implementation sequence, not authorization to bypass any control.

These seams touch several production components and persistence contracts. Implementing them opportunistically in this unit would risk changing live semantics or silently omitting controls; architectural review is required. Watcher archive limitations from Units 1–2 remain unchanged. No profitability or parity conclusion follows.

The historical XMRUSDT repeated-entry case was reviewed separately as a forensic regression specification in `XMR_INCIDENT_REGRESSION_CASE.md`. It does not establish that the Unit-3 global-state finding caused that incident; the requested post-isolation test remains deferred because isolation was not implemented.

خلاصهٔ فارسی: چند سرویس هنوز وضعیت و فایل‌های اجرای واقعی را به‌صورت سراسری می‌خوانند. اگر فقط یک container جدید بسازیم، تست تاریخی ممکن است همان وضعیت واقعی را مصرف یا تغییر دهد. برای همین این واحد را پیش از دست‌کاری کد متوقف کردم و مرزهای دقیق جداسازی را برای بازبینی ثبت کردم.
