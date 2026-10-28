# Application run scope — architecture review only

Baseline: source at HEAD `fc104a6`, checked against Unit-3 matrices; no implementation authorized. The full dependency inventory is [REPLAY_DEPENDENCY_OWNERSHIP_MATRIX.csv](REPLAY_DEPENDENCY_OWNERSHIP_MATRIX.csv). The answer is an explicit **composition-owned run scope**, but not a general service locator. Its only purpose is to own object lifetime and close/dispose *its own* resources. Components continue to receive narrow constructor dependencies directly. Do not use the existing lazy `bootstrap.Container.shutdown()` unmodified for replay: it clears the global broker registry.

## Scope ownership and policy

`ApplicationRunScope` should own a router (not auto-started), clock, SignalProcessor, fresh EngineService, FusionService plus fresh hierarchical symbol state, aggregator, StrategyManager with fresh adapters, one EnterpriseRiskManager/adapter, RiskEnforcement/guard, queue owner, claim/pending/position/cooldown state, isolated journals/trace sinks, and a broker execution port. It **references** a frozen configuration snapshot and immutable policy objects/parameters; it must not copy the user's `.env` into mutable replay state or read current global live services. A live scope uses the existing live adapters/persistence and real clock; a replay scope uses the same policy/config values, replay clock, in-memory state stores and a type/capability-restricted network-incapable simulated port. Composition chooses adapters, not decision branches. Symbols share intentionally portfolio-level risk *within one scope*, never across scopes; per-symbol state remains keyed by normalized symbol.

`SignalProcessor` already accepts a router but currently resolves a second global `application.containers.container` risk engine for price recording. Inject only a `record_price(symbol, close)` port referencing the scope's **same** risk manager used downstream; inject a forensic sink whose replay implementation cannot write production logs. Live composition passes adapters over the current live risk and logger. The event processor should not accept the whole global container. The module-level router may remain a backward-compatible live default while explicit composition uses a fresh router; importing the module currently starts the global router thread, so a later unit must remove that import-time start or isolate module import before claiming two replay contexts are thread-free. Merely constructing another `EventRouter` does not undo the import side effect.

`FusionService` must take a fresh `HierarchicalFusionService` per scope. That concrete class constructs `HierarchicalSymbolManager`, including its `SymbolStateMachine`, and holds three per-symbol state maps. Inspect its shared `hierarchical_logger` and confidence helpers for mutable/persistent effects before wiring replay. Inject the existing event clock only at multi-signal/neutral timestamp and decision-relevant state-transition reads; preserve Fusion weights, classification, thresholds and result algorithms. Live default remains the existing singleton until composed live parity proves safe.

`StrategyManager()` presently registers adapters in `__init__`; a new instance can be built, but adapters must be fresh and their nested `MarketStructureEngine`, `SetupEngine`, `DecisionPipeline`/caches checked. `BaseStrategyAdapter` stores `data_buffer`, `current_positions`, last-intent and exit timestamps, per-day counts, per-symbol cooldown/loss and debouncing state. Keep existing `StrategyConfig` values identical. Inject event time only at admission/expiry/daily-bucket and intent timestamp sites that currently read wall time; logging-only health timestamps need not be abstracted. Avoid resetting the module-level live `strategy_manager`.

Risk policy (exposure ceilings, leverage, cooldown duration, sizing and SL/TP rules) remains unchanged. Runtime state (positions, prices/correlation, daily PnL, cooldown expiry, active/pending orders, claims, circuit breakers and reconciliation) belongs to one scope. The queued auto-detection route remains the **only** execution owner. Its class-level `_claimed_intent_ids` becomes a scope-owned atomic claim store; duplicate deliveries in one scope share a claim, two scopes do not. This is in-process at-most-one pre-broker attempt, not broker/exchange exactly once. Broker timeout/restart retry remains `BROKER_RETRY_SEMANTICS_UNRESOLVED`.

The existing `LiveExecutionGuard` must still enforce the same risk decision before dispatch; current broker services import a global guard and journals, and the guard uses a global circuit-breaker manager. Future execution composition must inject the guard/breaker/journal/pending state together, without bypassing or weakening a veto. A replay adapter must have **no credentials, network client, broker registry reference, or live broker factory**; a mistaken boolean must not unlock exchange I/O. Type/capability tests should inspect the constructed dependency graph and fail if any network-capable port enters replay. Simulated fills and economic analysis are later units, not this review.

## Live compatibility contract

| Seam | Current live construction | Proposed live construction | Proof before switch |
|---|---|---|---|
| Router/processor | module globals; router starts at import | explicit live scope with same handlers/scheduling; compatibility global temporarily retained | subscriber graph and identical normalized Engine/Fusion/intent outputs |
| Fusion | global `fusion_service` binding global hierarchical instance | live scope initially passes that exact instance, then fresh-instance migration only after state/parity checks | same ordered signals, state transitions and vetoes on frozen fixture |
| Strategy | global `strategy_manager` | live scope initially references current manager; later constructor ownership only after identity/reconciliation test | same registered adapters, settings and selected intent |
| Risk/guard | global container risk plus guard/broker globals | live scope explicitly passes the *same* live instances, preserving policy | normalized size/order/risk/guard and F01/ownership regressions |
| Persistence | fixed/global live journals | live adapters point to existing paths; replay adapters point only to memory/temp | live fixture unchanged; replay hash-before/after and path-deny tests |

Do not claim equivalence merely because constructor signatures look similar. Switch each live binding only after its comparison test passes; rollback is the prior default wiring, never a changed trading policy. The existing active XMR safety blocker is retained.

## Rejected designs

| Proposal | Verdict and reason |
|---|---|
| Monkeypatch global container during replay; temporarily replace singleton instances | REJECT: simultaneous runs/live threads can observe swapped state, and restoration after exceptions is unsafe. |
| Clear live state before replay | REJECT: destructive to positions, claims, cooldown and operator safety. |
| Copy the live pipeline into a replay pipeline; separate replay StrategyManager | REJECT: semantic drift and duplicate policy authority. |
| Bypass Risk, cooldown or position checks in historical mode | REJECT: invalid parity and misleading intents. |
| Mock FusedSignal or enter directly at StrategyManager | REJECT as **canonical** replay: omits watcher/Engine/Fusion and selection. Useful only for a separately labeled unit fixture. |
| `if backtest: datetime...` in strategy/domain logic | REJECT: two decision semantics; inject a clock at time-dependent boundaries. |
| Use production journals read-only | REJECT: contaminates initial state and some constructors mutate/create/rename files; not even structurally read-only. |
| Reuse existing concrete components with explicit scoped dependencies and memory-backed ports | ACCEPT for staged implementation, subject to the release gates and no policy changes. |

## Objective release gates before full replay

A. No replay-reachable global mutable decision state. B. No production persistence reachable. C. All decision time uses controlled event clock. D. Fresh Fusion/Strategy/Risk state per run. E. Live normalized decisions unchanged. F. One queued owner and same-ID at-most-one pre-broker attempt. G. Zero network capability. H. Two simultaneous contexts remain isolated. I. Production persistence hashes unchanged after tests. **Only after A–I** may full decision-level prefix invariance and live/replay parity be attempted. A later watcher-data gate remains separate; missing order-flow/tick/screener history must not be invented.
