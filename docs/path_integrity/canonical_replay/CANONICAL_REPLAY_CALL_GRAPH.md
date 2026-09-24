# Current call graphs and first divergence

Live auto-detect (source/Unit-3 offline composition): CLI → lifecycle/container → `AutoDetectionOrchestrator` → live watcher(s) → global `EventRouter.MARKET_OBSERVATION` → `SignalProcessor._process_observation` → `EngineService.process_observation` → `INTERPRETED_SIGNAL` → `FusionService.fuse_signals([signal])` → `FUSED_SIGNAL` → global `SignalAggregator` (wall-clock/threaded) → `StrategyManager.evaluate_fused_signal` → `ExecutionIntent` → auto-detection queue/claim → order preparation → RiskEnforcement/LiveExecutionGuard → broker boundary.

Legacy backtest: historical row → named adapter `generate_signal()` → mock `FusedSignal` → adapter `evaluate_fused_signal()`; first divergence is **before** canonical watcher/Engine/Fusion/aggregator competition. It remains `LEGACY_NONCANONICAL` and untouched.

New input primitive: `ClosedBar` → `HistoricalClosedBarSource.completed_through(T)` → **STOP**. It does not invent a `MarketObservation` or enter the decision graph. Live Fusion currently receives individual interpreted signals in the inspected `SignalProcessor`; do not replace that with hypothetical batched Fusion semantics.
