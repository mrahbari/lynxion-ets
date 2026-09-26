# Autonomous canonical replay program

## P — observation-price contract investigation

- Start: `c8e8bda`; end: this documentation/forensic-seam unit commit. No price-contract implementation.
- All `MarketObservation` constructors found: funding, liquidity, anomaly-ML, orderflow-WS, trend-MTF, tick, historical-candle, market-pulse (two), volatility, CMC screener, and a Fusion-created mock observation. `observation_value` is polymorphic (funding rate, liquidity score, imbalance, trend/momentum/volatility/anomaly and screener metrics), **not a universal market price**.
- Historical-candle and market-pulse include `metadata.latest_candle`, which may contain close; CMC screener has `metadata.cmc_data.price`. The remaining producers have no uniform causal price field. Several use wall-clock observation timestamps. Classification: candle/pulse = PRICE_DERIVABLE_CAUSALLY only after per-producer close-time provenance is verified; CMC = AMBIGUOUS due to quote/time semantics; other analytic observations = NON_PRICE_ANALYTICAL or UNKNOWN. None establishes a universal `observation.close` contract.
- `SignalProcessor._process_observation` attempts `float(observation.close)` inside `except Exception: pass`; canonical entity has no `close`. Other `record_price` call: legacy `infrastructure/backtest/realistic_backtester.py` records `execution_price` directly, not in the canonical live observation route. The risk manager stores prices for rolling correlation (`price_history_for_correlation`); therefore the broken call is potentially decision-relevant, not safely removable as redundant. Current classification: **AUTHORITATIVE_BUT_BROKEN in the inspected live observation path**, subject to any external uninspected price feed; no unique replacement contract established.
- Multiple plausible contracts would alter risk semantics. Status: `PRICE_CONTRACT_OPERATOR_DECISION_REQUIRED`; price recorder and exception policy parked. No `observation_value == price` assumption, no silent fallback.

## A-partial — explicit forensic sink

- Start: `c8e8bda`; changed production file: `infrastructure/messaging/event_system.py`; test file: `tests/unit/test_signal_processor_forensic_seam.py`; documents: this log, canonical manifest/test results.
- Existing live constructor keeps lazy access to the identical module-level forensic logger. An explicit sink can handle subscribed Engine/Fusion forensic calls without writing via the global logger. The retained legacy direct handler uses the same seam; its execution ownership is unchanged. Price/container lookup remains as-is pending contract decision.
- Focused result: 46 passed / 0 failed (new forensic tests plus Unit-1/2 and ownership/runtime-wiring regression slices). Broker network activity: NONE in the new tests; no broker adapter was constructed by them. Protected production persistence hashes matched their previously documented values after tests; no before/after snapshot was taken in this unit, so this is a limited unchanged-from-record check.
- Status: `IMPLEMENTATION_A_PARTIAL`. Open: price contract, remaining global container lookup, later B–G seams, full causal/parity tests. XMR remains `XMR_ROOT_CAUSE_UNRESOLVED`; broker retry semantics unresolved. Next independent authorized action: assess Fusion instance seam from current source; do not infer that A is complete.

## B — Fusion instance and event-clock seam

- Start: `058f5ac`; end: this bounded B commit. Changed production files: `infrastructure/fusion/fusion_service.py`, `infrastructure/fusion/hierarchical/hierarchical_fusion_service.py`, `infrastructure/fusion/hierarchical/symbol_state_machine.py`; new test: `tests/unit/test_fusion_instance_seam.py`.
- `FusionService` can receive an explicit hierarchical instance and clock. `HierarchicalFusionService` constructs a fresh `HierarchicalSymbolManager`/`SymbolStateMachine` and accepts the same clock. Live defaults still reference the prior global hierarchical instance and `LiveClock`; algorithms, weights and thresholds were untouched. Decision/result timestamps in the touched Fusion paths now use the supplied clock. Hierarchical logger stays the existing observability dependency by default and may be supplied explicitly; its wall-clock debug timestamps remain observability-only, not normalized decision output.
- Focused regression: 52 passed / 0 failed. Tests establish live singleton identity, two independent scoped hierarchical state machines, per-symbol isolation, and injected-clock neutral output. They do **not** prove full live/replay parity or that all nested Fusion helpers are isolated; the latter remains for ApplicationRunScope review.
- Protected production persistence hashes matched the prior Unit-3 documented hashes after testing; no fresh pre-test snapshot was taken, so this is not a complete before/after persistence proof. New tests did not create a broker or authenticated network client. Status: B seam verified for the tested scope, program still partial. Next: source-audit StrategyManager/adapter state for C; stop on any policy ambiguity.

## C — existing fresh StrategyManager construction, bounded verification

- Start: `2c50834`; changed production files: NONE. Added `tests/unit/test_strategy_instance_scope.py` and this documentation.
- Source shows `bootstrap/container.py` constructs a `StrategyManager()`; its constructor registers fresh adapter instances. `BaseStrategyAdapter` initializes per-instance buffers, positions, intent/cooldown/loss dictionaries; setup-based adapters construct fresh nested market-structure/setup/pipeline instances. Module-level legacy `__getattr__` fallback remains outside explicit composition and must not be used by replay.
- Two independently constructed managers have identical registered strategy names but distinct adapters, mutable dictionaries/lists, and nested engines where present. Mutation in one does not affect the other; unregistering in one does not change the other. Focused test: 2 passed / 0 failed. This proves a fresh-instance seam exists without production changes, **not** full strategy decision/time parity. `StrategyConfig` still reads live settings implicitly, and some adapter timestamp fallbacks use wall time; explicit event-time/config binding remains a later composition gate. Status: C instance-scope verified for tested fields, full C decision-time contract PARTIAL.
- No broker/network action was made by this test. No production persistence was intentionally accessed, but no fresh before/after hash snapshot was collected. Next: inspect D risk/persistence source dependencies before editing; do not infer safe isolation from StrategyManager alone.

## D1 — narrow RiskEnforcement journal/gate injection

- Start: `a21c0f9`; changed production file: `infrastructure/risk/risk_enforcement.py`; new test: `tests/unit/test_risk_enforcement_state_seam.py`.
- Source dependency: constructor read `data/sl_cooldown_journal.json` through a fixed constant; save used the same fixed path. `record_stop_loss_exit` and `record_take_profit_exit` bypassed an injected gate and called the global singleton. Added an optional journal path and consistently used the injected cooldown gate when supplied. Defaults retain the same live path and singleton fallback. No risk limit, sizing, cooldown duration, or rejection rule changed.
- Focused suite including F01 sizing and execution ownership: 48 passed / 0 failed. Explicit temporary journals and gate spy verify isolation in this slice. Four protected production persistence hashes after tests matched previously documented hashes; no fresh pre-test hash snapshot was collected. New test did not instantiate broker/network clients.
- Status: D **PARTIAL**. Other fixed/persistent risk, cooldown, active-order and reconciliation dependencies remain. This does not authorize replay scope construction or economic tests. Next: bounded audit of remaining D dependencies and E claim ownership; continue only if independently safe.

## E1 — scope-owned intent claim with unchanged live default

- Start: `199b26d`; changed production files: `infrastructure/orchestrators/_auto_detection_execution.py`, `auto_detection_orchestrator.py`; new test: `tests/unit/test_intent_claim_scope.py`.
- Previous claim lock/set were class-level. `IntentClaimStore` encapsulates the same atomic in-process set. The queued owner accepts an optional store; omitted/default construction uses one shared process-wide live store, retaining cross-instance duplicate protection. An explicit store allows a replay scope to own claim lifetime. The queued route remains the only authoritative owner; no broker retry or process-restart semantics were altered.
- Focused claim, concurrency, ownership and F01 regressions: 45 passed / 0 failed. No broker/client was constructed by the new claim tests. This proves only atomic claim behavior at the isolated seam, not an end-to-end pre-broker invariant for a future replay scope. Production persistence hashes were not freshly snapshotted before/after this run.
- Status: E **PARTIAL**. Pending-order, active-position and cooldown state are still shared/global; broker retry semantics `UNRESOLVED`. XMR remains `XMR_ROOT_CAUSE_UNRESOLVED`. Next: audit whether F can be safely composed without these remaining dependencies; do not instantiate a network-capable replay.

## D2 — cooldown decision-time seam

- Start: `f0f434a`; changed production file: `infrastructure/risk/symbol_cooldown_gate.py`; new test: `tests/unit/test_cooldown_event_clock_seam.py`.
- An explicitly constructed gate can use `ReplayClock` for startup loss reconciliation, stop/target exit timestamps, and admission expiry. Default construction uses `LiveClock`, preserving wall-clock live semantics. Existing 60-minute/24-hour/15-minute rules, blacklist, journal format, and singleton live accessor were not changed.
- Focused tests including risk/route regressions: 39 passed / 0 failed. An explicit temporary gate rejects at event time and allows after the unchanged 60-minute interval. This proves deterministic time only for this gate, not all risk/execution time. New tests used no broker/network client and temporary persistence paths. Full production persistence before/after hashes remain a future release gate.
- D remains PARTIAL: EnterpriseRiskManager, reconciliation, active/pending-order state and other fixed paths are not isolated. F/G and economics remain unauthorized. Next: inspect remaining persistent state and decide if a bounded seam exists or a hard-stop architecture issue is reached.

## Program checkpoint — release gates and stop boundary

Combined focused regression (all six new seam tests plus Unit-1/2, F01, pending tracker and path-integrity slices): **77 passed / 0 failed**. SHA-256 of `active_positions_journal.json`, `live_order_journal.json`, `sl_cooldown_journal.json`, and `trade_journal.csv` was identical immediately before and after this combined run (respectively `11107b33...`, `e72c03f3...`, `d585dce9...`, `1eb076e6...`). Existing unrelated C-11/C-35 working-tree changes were neither staged nor edited. No authenticated broker request/order was performed; the replay/broker boundary was not constructed.

| Gate | Current evidence |
|---|---|
| A no replay-reachable mutable global | FAIL/NOT ESTABLISHED: SignalProcessor price container, pending tracker, orchestration globals remain |
| B no production persistence reachable | FAIL/NOT ESTABLISHED: reconciliation and live journal defaults remain reachable |
| C controlled replay decision clock | PARTIAL: Fusion/cooldown/aggregator seams only; Risk/strategy/execution time remains |
| D fresh Fusion/Strategy/Risk state | PARTIAL: Fusion and Strategy tested; Risk only narrow journal/gate seam |
| E live normalized decisions preserved | NOT TESTABLE end-to-end; focused default/identity regressions passed |
| F one execution owner | Prior offline production composition confirmed; full future replay not constructed |
| G zero network capability | NOT ESTABLISHED structurally for ReplayScope; no ReplayScope exists |
| H simultaneous scopes isolated | NOT TESTABLE |
| I production persistence unchanged | PASS for this combined test only; not a general replay guarantee |
| J decision prefix invariance | NOT TESTABLE |
| K applicable live/replay parity | NOT TESTABLE |

Remaining source-proven obstacles: `EnterpriseRiskManager` starts a background correlation thread in its constructor and reads wall time for daily/position events; `PendingOrdersTracker` is a class-state singleton used directly by orchestrator and broker services; `BrokerReconciliationService` loads a fixed active-position journal. Their safe composition is not established by the narrow seams. The price recorder additionally has an unresolved trading/risk semantic choice (Phase P); resolving it requires operator decision under H5. These are not reasons to fabricate a replay path or relax risk controls. Final program status at this checkpoint: `CANONICAL_REPLAY_BLOCKED_BY_POLICY_DECISION`; baseline NOT authorized. XMR and broker retry/restart remain unresolved. Exact next action: decide the causal per-observation market-price contract, then continue bounded D/E state and persistence seams with live-parity tests before F/G.

Watcher matrix correction at this checkpoint: the older HistoricalCandleWatcherAdapter row still asserted `datetime.now()` despite the Unit-2 timestamp fix. It now says UNKNOWN for full feature/input parity while acknowledging that historical close/event time is preserved. No watcher coverage or parity status was upgraded.

## P + A completion after operator contract decision

- Start: `b95013d`; production files changed: `domain/entities/signal.py`, `infrastructure/messaging/event_system.py`, `infrastructure/watchers/adapters/tick.py`; added `tests/unit/test_market_observation_price_contract.py`. Price contract and producer classifications are recorded in `IMPLEMENTATION_A_SIGNAL_PROCESSOR_SEAM.md`.
- `market_price` is optional and producer-explicit. No analytical `observation_value` or arbitrary metadata is inferred as price. Only the tick producer qualified for automatic population in this pass. Candle/pulse/screener remain unpopulated pending source/time proof; this does not block non-price observations.
- Explicit recorder composition bypasses the legacy global container; default live adapter delegates through the existing bridge to the same intended risk runtime. Forensic sink and router seams from earlier commits remain unchanged. Missing/invalid price still permits Engine processing; invalid values and recorder errors are logged. No risk/strategy policy changed.
- Focused regression: **64 passed / 0 failed**, 26 warnings. Protected production persistence SHA-256 before and after matched exactly: `11107b33...`, `e72c03f3...`, `d585dce9...`, `1eb076e6...`. Network/broker action: NONE in the new tests. Status: `IMPLEMENTATION_A_VERIFIED` for the explicit dependency contract, not full replay.
- Next authorized unit: continue D/E per-run risk/pending/reconciliation isolation from current source; do not construct F while fixed production paths or background decision threads are reachable. Price contract is no longer a policy blocker. XMR and broker retry statuses unchanged.

## D3 — reconciliation active-position journal seam and test isolation

- Start: `b5df2c2`; changed production file: `infrastructure/execution/broker_reconciliation.py`. Optional `active_positions_journal_path` now controls both load and atomic save; omitted/default path is unchanged. New `tests/unit/test_reconciliation_journal_scope.py` proves two temporary journal instances do not share active-symbol state. No broker/reconciliation decision rule changed.
- Safety finding during initial regression: `data/sl_cooldown_journal.json` had a new SHA-256 value (`0607bcea...` versus the previously recorded `d585dce9...`). No immediate pre-test snapshot was taken, so the initial change cannot be assigned conclusively to this run. Source inspection showed the existing B4 reconciliation fixture isolated only active-position journal while closure tests could call the global cooldown gate. **Do not erase or restore the journal without separate authority.**
- Corrective test-only change: the B4 fixture now provides a temporary `SymbolCooldownGate` journal and trade-journal path. The same 20 focused reconciliation/closure tests passed; all four protected production persistence SHA-256 values were identical immediately before and after this corrected run. No authenticated broker request/order was made; tests use fake broker objects.
- Status: D3 seam TEST_VERIFIED, but D overall PARTIAL. Reconciliation also depends on other journal/identity/guard resources; a replay scope is not yet safe. Next: audit pending-order state and EnterpriseRiskManager worker/time without changing risk policy. Price contract remains resolved; XMR and broker retry remain unresolved.

## E2 — scoped pending-order state core

- Start: `d894fb3`; production files changed: `infrastructure/shared/pending_orders_tracker.py`, `infrastructure/orchestrators/auto_detection_orchestrator.py`; new test `tests/unit/test_pending_orders_scope.py`.
- The previous class-state tracker rules were moved into one `PendingOrdersState` implementation with a caller-owned clock and lock. The existing process-wide `PendingOrdersTracker` singleton/class API delegates to one live state, preserving legacy callers and duplicate/30-second expiry semantics. AutoDetectionOrchestrator accepts an optional pending state; its default remains the live facade. No broker calls or order-routing ownership changes.
- Focused prior tracker, scope and route/claim regressions: 50 passed / 0 failed. Two scoped states do not contaminate each other or the live facade; expiry follows the supplied event clock. Four protected persistence hashes were identical immediately before/after this run. New tests used no broker/network adapter.
- Status: E2 TEST_VERIFIED at the tracker/AutoDetection seam, E overall PARTIAL. Broker execution services still invoke the live class facade directly, so full replay execution would not yet be isolated. Do not build F/G or run economics until this is resolved with live-compatible injection. XMR and broker retry remain unresolved.

## Hard-stop checkpoint — Risk correlation timing is decision-relevant

- Start: `e622908`; this checkpoint is documentation-only. `EnterpriseRiskManager.__init__` starts a daemon `_correlation_worker_loop`; it sleeps for 10 wall-clock seconds then updates `correlation_matrix` from recorded prices. `ConsolidatedRiskEngineAdapter` reads that matrix through `calculate_correlation_penalty` and passes the penalty into `calculate_position_size`, where it divides risk allocation. Therefore worker timing can change pre-broker quantity. It is **not** merely observability state.
- A replay-only choice to update correlations after every bar, on event-time 10-second boundaries, or never would produce different risk sizes from each other and potentially from live's unsynchronized worker. No source-defined deterministic event-time scheduling policy identifies one as equivalent. Disabling the thread without replacing its decision semantics would weaken/change Risk. Changing live scheduling to a deterministic event-time rule could also alter live sizing. This is H5/H10, not a harmless class/constructor decision. No change to `EnterpriseRiskManager` was made.
- One independent capability remains conceptually possible: replay should use a structurally network-incapable simulated broker, so live `BrokerExecutionService` and its global pending tracker should not be constructed. This is not yet proven by a composition graph. E2 establishes local pending state only at the tracker/AutoDetection boundary. Do not upgrade E/F/G on that inference.
- Combined focused regression across the new seams and prior causal/ownership/F01/reconciliation tests: **111 passed / 0 failed**, 26 warnings. Four protected persistence SHA-256 values matched immediately before/after this run (active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`). The earlier cooldown-journal hash change had no before snapshot and remains unattributed; it was not reverted. No authenticated broker request or order was made by this program turn.

| Release gate | Checkpoint |
|---|---|
| A no replay-reachable mutable global | NOT MET: several global application/execution dependencies remain |
| B no production persistence reachable | NOT MET: full composition does not exist |
| C deterministic decision clock | PARTIAL: Fusion, cooldown, pending and aggregator seams; Risk correlation worker remains wall-clock |
| D fresh Fusion/Strategy/Risk runtime | PARTIAL: Fusion/Strategy tests pass; Risk worker/persistence scope unresolved |
| E live normalized semantics preserved | PARTIAL focused regressions only; no end-to-end parity |
| F one execution owner | Previously offline-verified live composition; future replay scope not constructed |
| G zero replay network capability | NOT TESTABLE: no ReplayScope |
| H simultaneous replay contexts isolated | NOT TESTABLE |
| I production persistence unchanged | PASS for the 111-test checkpoint only |
| J canonical decision prefix invariance | NOT TESTABLE |
| K live/replay parity | NOT TESTABLE |

Final program status at this hard stop: `CANONICAL_REPLAY_BLOCKED_BY_POLICY_DECISION`. `PREFIX_INVARIANCE_NOT_TESTABLE`; `LIVE_REPLAY_PARITY_NOT_TESTABLE`; `XMR_ROOT_CAUSE_UNRESOLVED`; `BROKER_RETRY_SEMANTICS_UNRESOLVED`. Economic baseline is **not authorized**. Historical order-flow/tick/screener inputs remain unavailable; full watcher parity is not possible with the current archive, independently of this Risk timing blocker.

Exact next action requiring review: define how the decision-relevant rolling-correlation update is scheduled in a canonical event-time contract, and whether live Risk scheduling may be changed to that contract with controlled parity/regression evidence. Until that decision, do not start ApplicationRunScope F, replay G, or baseline. Continue no additional policy-affecting Risk edit by inference.

## Risk correlation scheduling contract review

- Start HEAD: `42b9985`; reviewer required unchanged Live scheduling. New source audit and three network-free tests are in `RISK_CORRELATION_SCHEDULING_AUDIT.md` and `RISK_CORRELATION_SCHEDULING_TRACE.csv`. No production source/configuration was changed.
- Existing Live worker first sleeps 10 wall-clock seconds, then recalculates using the price history present when it gets the lock. Subsequent sleeps start after each calculation. Prices have no stored event timestamps; worker update and sizing have no shared ordering boundary. A penalty read immediately before versus after the worker's matrix assignment can change dynamic quantity for identical market-price inputs (focused test: 10 versus 8.333333 units).
- Formula/window/minimum samples and Risk policy were not changed. Empty-data recalculations are idempotent, but that does not resolve worker-vs-order interleaving. A replay-only deterministic tie-break cannot be asserted equivalent to existing Live.
- Status: `CORRELATION_PARITY_BLOCKED_BY_LIVE_CONCURRENCY`; `LIVE_CORRELATION_ORDERING_NONDETERMINISTIC`. The smallest future change is an explicitly serialized ordering/anchor contract shared by Live and replay, requiring separate Risk-semantic review. F/G and economic baseline remain unauthorized; prefix invariance and live/replay parity remain NOT TESTABLE.
- Expanded focused regression: 114 passed / 0 failed, including new forensics, price contract, A/B/C/D/E, source causality, F01, execution ownership, pending-order and reconciliation slices. Four protected production persistence hashes matched immediately before/after. No broker or authenticated network activity was performed. Existing C-11/C-33/C-35/Compression artifacts were not touched by this unit; C-35 is `C35_MONITORING_UNAVAILABLE_IN_CURRENT_ENVIRONMENT` and was not polled. XMR/broker retry remain unresolved.

## Correlation A–D design review

- Start `35b5c4e`; documentation-only review in `CORRELATION_SNAPSHOT_DESIGN_REVIEW.md`. No production source, config or test behavior changed in this unit.
- Atomic outer-matrix publication exists today, but penalty calculation reads that reference for each portfolio symbol without a lock or captured version. A worker publication can cause one sizing decision to consume mixed versions. A single immutable snapshot would solve that narrower problem but can itself alter quantity in a multi-position race; it does not fix worker-vs-sizing timing.
- Serializing all Risk operations or refreshing before sizing defines new economically effective ordering. Merely recording published/consumed snapshots could support prospective trace replay, not historical reconstruction, because old publication times and price cutoffs were not archived. None of A–D meets the no-economic-order-change plus strict parity conditions; no correlation production edit was made. Continue independent ApplicationRunScope seams only where live defaults can be preserved.

## F-prep — explicit ArchitectureOrchestrator processor/aggregator bindings

- Start `892a57f`; production file `infrastructure/orchestrators/architecture_orchestrator.py`; new test `tests/unit/test_architecture_orchestrator_scope_seam.py`. Constructor accepts optional explicit SignalProcessor and SignalAggregator; omitted defaults still bind the exact legacy global instances. `start()` now calls the bound aggregator/processor rather than module globals. An explicit processor/router mismatch fails at construction. No strategy, Fusion, Risk or execution policy changed.
- Focused router/price/path regression: 56 passed / 0 failed. Expanded applicable prior slices plus this seam: **117 passed / 0 failed**, 26 warnings. Two explicit routers/processors subscribe independently, and the live router subscription count is unchanged. Four protected production persistence hashes matched immediately before/after the expanded run. No broker/network adapter was used by the new tests.
- This is a **partial orchestration seam**, not ApplicationRunScope. Module import still starts the global event-router thread. `ArchitectureOrchestrator.start()` still writes the global orchestrator execution-service field, and `stop()` clears global pending orders and broker registry; those paths must not be used for replay until separately isolated. Correlation ordering remains parked and economic baseline forbidden.

## F-prep — explicit ownership of legacy global lifecycle effects

- Start `fb25f9d`; production file `architecture_orchestrator.py`, prior focused test extended. Optional `owns_live_globals=True` preserves the existing Live start publication and stop cleanup. A scope explicitly passing `False` uses its injected aggregator/processor but does not publish execution service to the global orchestrator or clear the live pending tracker/broker registry on stop. This is infrastructure lifetime ownership, not a strategy/Risk/broker policy branch.
- Focused isolated lifecycle test: 4 passed / 0 failed. Expanded relevant regression: **118 passed / 0 failed**, 26 warnings. Four protected persistence SHA-256 hashes matched immediately before/after. No broker adapter was constructed or network call made by the new test.
- This still does not close the global import-time router thread or provide scoped cleanup of pending/order/reconciliation state; `ApplicationRunScope` is not yet constructible. Do not use this seam to claim full state isolation or parity. Correlation branch remains parked.

## Correlation consumption contract — reviewer-authorized unit

- Start `ee569dd`; production files `application/risk_management/enterprise_risk_manager.py` and `infrastructure/risk/risk_engine_adapter.py`; new `tests/unit/test_risk_correlation_snapshot_contract.py`; detail in `CORRELATION_SNAPSHOT_CONTRACT.md`. The Risk adapter pins one immutable version at the start of dynamic sizing; publication later in that call cannot alter its penalty. Legacy Live worker cadence and all numerical formulas remain unchanged.
- Expanded focused regression **125 passed / 0 failed**. Four protected persistence SHA-256 hashes unchanged before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. No authenticated broker/network activity.
- `CORRELATION_SNAPSHOT_CONTRACT_VERIFIED`; `LIVE_DECISION_BOUNDARY_STILL_NONDETERMINISTIC` as to which worker version is latest at a future intent start; `HISTORICAL_CORRELATION_SCHEDULE_NOT_RECONSTRUCTABLE`. Next safe unit: explicit event-time replay publication scheduler, then continue other ApplicationRunScope dependencies. No baseline authorized.

## Replay correlation scheduler — bounded event-time unit

- Start `b153285`; production source `EnterpriseRiskManager` gains an optional worker-start seam (default `True`, unchanged Live), and a new `ReplayCorrelationScheduler` drives the same calculation with `ReplayClock`. See `REPLAY_CORRELATION_EVENT_TIME_CONTRACT.md` for the replay-only `T0 + 10 seconds` anchor and batch/tie ordering.
- Same-timestamp prices precede an exactly due publication and then sizing. Earlier gap boundaries are calculated before later prices can enter history. Duplicate timestamp batches fail. No worker, sleep, wall-clock or network in replay tests. Focused and applicable prior regressions: **131 passed / 0 failed**. Four protected production persistence hashes unchanged before/after.
- `HISTORICAL_CORRELATION_SCHEDULE_NOT_RECONSTRUCTABLE` remains; do not upgrade full Live/Replay historical timing parity. Next: continue ApplicationRunScope dependencies and canonical decision wiring. Baseline still forbidden.

## D/E-prep — queued-owner Risk and cooldown dependencies

- Start `3ecbdd7`; production files `auto_detection_orchestrator.py` and `_auto_detection_execution.py`; new `test_auto_detection_risk_scope_binding.py`. Optional Risk-engine and cooldown-gate dependencies now serve both the opportunity loop and queued pre-broker path. Omitted dependencies retain the existing global Live lookups and rejection behavior; explicit dependencies avoid the global Risk container/cooldown singleton in these specific calls. No Risk/cooldown rule changed.
- Focused offline tests verify explicit identity, default global fallback, and an execution-intent cooldown rejection through the injected gate. Expanded applicable regression **134 passed / 0 failed**. Four protected persistence hashes matched immediately before/after. No broker/network adapter in new tests.
- This is a **partial seam**. AutoDetection construction still starts global architecture, constructs a live watcher and notification services, and its execution path has other global/network-capable fallbacks. Do not construct it as a ReplayScope yet. Historical correlation timing remains unreconstructable; baseline forbidden.

## E-prep — queued-owner event-time stamps

- Start `d573cde`; execution-owner constructor accepts an optional clock. Pending-intent, portfolio and pre-broker order timestamps use that clock; the omitted default uses `LiveClock` and retains wall-clock Live behavior. No timing threshold or Risk policy changed.
- Focused execution/correlation tests: **49 passed / 0 failed**. Expanded applicable regression: **136 passed / 0 failed**. Four protected production-persistence SHA-256 values matched before/after. Tests made no authenticated broker request.
- Partial only: the heartbeat guard, live watcher scheduling, price fallback and constructor globals remain distinct blockers. No ReplayScope or decision-level prefix/parity claim is made. Historical correlation wake-up timings remain unavailable.

## F-prep — queued-owner explicit construction and teardown

- Start `16c1659`; `AutoDetectionOrchestrator` may now bind an explicitly supplied canonical architecture orchestrator, opportunity watcher and risk-alert service. The omitted default retains the same global Live services, watcher constructor and notification construction. Explicit construction does not create a second strategy/engine/Fusion implementation.
- Teardown now stops the instance's architecture and clears the instance's pending-order tracker; the default Live instances remain those previously used. A two-owner test proves distinct ExecutionIntent subscriptions and isolated teardown. Expanded applicable regression **137 passed / 0 failed**; four protected production persistence hashes unchanged; no network/broker activity.
- **Still partial:** a replay-safe owner is not constructed. Forward-exit activation, constructor imports, market-price fallback (including exchange lookup/random default), heartbeat guard and other execution dependencies remain to be addressed. No policy has been chosen for missing historical execution price. Full replay/parity/baseline forbidden.

## E/F-prep — explicit causal execution-price source

- Start `f772886`; `AutoDetectionOrchestrator` accepts an optional execution-price source. When supplied, the queued owner asks it for symbol/event-time price and fails closed with `MARKET_PRICE_UNAVAILABLE` on absent/nonfinite/nonpositive price, before Risk or broker. This path cannot fall through to the existing live repository, exchange lookup or synthetic/random default. Omitted source retains the exact prior Live fallback behavior; no Live trading policy changed.
- Four invalid/missing-price fixtures plus prior tests: expanded applicable regression **141 passed / 0 failed**. Protected persistence hashes unchanged; no authenticated network/broker activity. The future replay composition must provide a strictly causal network-incapable source and a simulated broker; neither full composition nor positive-path parity is claimed here.

## E/F-prep — scoped heartbeat decision time

- Start `3e41773`; `SignalProcessor` now accepts an optional clock for heartbeat recording (omitted default `LiveClock`) and exposes a narrow heartbeat-time query. The queued owner may consume an explicit heartbeat source; if supplied, the existing 90-second freshness check applies even to a simulated execution service at event time. The omitted Live source and existing simulated-service default bypass remain unchanged.
- Focused test exercises observation processing and source query at ReplayClock time; owner test covers stale/missing/fresh at the unchanged threshold. Expanded applicable regression **143 passed / 0 failed**; four protected persistence hashes unchanged; no network/broker activity. The retired direct handler still contains wall-clock code but is not an ExecutionIntent subscriber. Full decision parity is not claimed.

## D/F-prep — Risk lifecycle event clock

- Start `423a5cd`; `EnterpriseRiskManager` now accepts an optional clock. Daily-start/reset and position entry/exit timestamps use it. Omitted default remains `LiveClock`; worker-start and correlation scheduling defaults remain unchanged. No Risk formula, threshold, fee or exposure policy changed.
- A fake trade tracker proves replay event-time entry/exit and UTC day rollover without touching the production tracker. Expanded applicable regression **145 passed / 0 failed**; four protected persistence hashes unchanged; no network/broker activity. The production-global trade tracker still needs an explicit scope seam before position lifecycle may be used in replay.

## D/F-prep — Risk trade-tracker ownership

- Start `389bdc5`; `EnterpriseRiskManager` now accepts an optional trade-tracker instance for entry/exit recording. Omitted default remains the existing global Live tracker. An explicit tracker test makes the global fail if touched, then proves the local tracker receives causal entry/exit timestamps. No position/Risk policy or journal format changed.
- Expanded applicable regression **145 passed / 0 failed**; four protected persistence hashes unchanged; zero authenticated broker/network activity. This isolates this manager's two tracker calls only, not every persistence path of a full ReplayScope.

## F-prep — forward-exit activation ownership

- Start `e1e6998`; AutoDetection now accepts an optional forward-exit bundle factory. Omitted construction calls the same Live builder; explicit composition can supply a no-production-write factory. A scoped-constructor test makes the global builder fail if called. No XMR blocker, exit rule or Live observer default changed.
- Expanded applicable regression **145 passed / 0 failed**; four protected persistence hashes unchanged; zero authenticated broker/network activity. This closes one constructor side effect, not the full ReplayScope dependency graph.

## F — isolated canonical decision-scope slice

- Start `48ce1e3`; new `ReplayDecisionRunScope` owns ReplayClock, fresh router, Engine, hierarchical Fusion/FusionService, StrategyManager, synchronous SignalAggregator, SignalProcessor, worker-free Risk manager, local trade tracker and forensic trace sink. It feeds causal `MarketObservation` through the **same** event handlers and has no execution service/broker or order capability. It does not turn rows into mock fused signals.
- Two-scope test proves mutable instance separation, no cross-subscriptions, no broker object, no scoped router thread, causal risk-price/heartbeat state, and repeatable reached event-type trace. Expanded applicable regression **147 passed / 0 failed**; four protected persistence hashes unchanged; socket connection prohibited in the focused test; no broker/network activity.
- This is **not** full `ApplicationRunScope`: no queued owner, RiskEnforcement/order service/guard/simulated broker, historical watcher reconstruction or scheduler integration. It is not a full canonical replay run. `PREFIX_INVARIANCE_NOT_TESTABLE` and `LIVE_REPLAY_PARITY_NOT_TESTABLE` remain; baseline forbidden.

## G-prep — completed-bar historical watcher subset

- Start `68be87a`; `ClosedBarDecisionDriver` feeds the **existing** HistoricalCandleWatcherAdapter only from validated completed bars into the isolated canonical decision scope. It preserves close time and supplies explicit causal `market_price=bar.close`; no order-flow/tick/screener or MTF proxy is manufactured. This is a defined subset, not a full live watcher reconstruction.
- Two tests cover prefix-plus-future stability through T, two-symbol watcher buffer separation, causal Risk price history and idempotent incremental driver calls. Expanded applicable regression **149 passed / 0 failed**; protected persistence hashes unchanged; no network/broker activity. Full decision-level prefix and live/replay parity remain NOT TESTABLE because execution/Risk/order and unavailable watchers are not yet wired.

## E/F-prep — guard circuit-breaker lifetime and event time

- Start `1b77289`; `CircuitBreaker` accepts an optional clock and `LiveExecutionGuard` an optional breaker lookup. Omitted defaults retain LiveClock and the process-global breaker manager. A scoped guard can consume a separate event-time breaker without changing failure threshold, reset interval or Guard precedence.
- Focused tests cover two isolated guards, deterministic open/reset time, and Live default. Expanded applicable regression **162 passed / 0 failed**; four protected persistence hashes unchanged; no authenticated broker/network activity. The execution truth ledger, BrokerExecutionService and real queued owner are not yet bound into a full replay execution scope.

## F-prep — network-incapable broker boundary

- Start `f1ee5cb`; added `SimulatedBrokerAdapter`, a local BrokerAdapter port implementation that records accepted orders with deterministic IDs, supports local cancellation/status/open-order queries, and never assumes a fill, fabricates order-book depth, calculates Risk/PnL or contains credentials/network clients. It is **not yet wired** to the authoritative queued owner or Guard.
- Focused test proves deterministic independent instances and no automatic position; expanded applicable regression **163 passed / 0 failed**. Four protected persistence hashes unchanged; no authenticated broker/network activity. Full pre-broker semantic parity and baseline remain forbidden.

## E/F-prep — scoped existing BrokerExecutionService

- Start `32968b0`; the **existing** BrokerExecutionService accepts a complete explicit adapter/Guard/ledger/pending-state/validator/forensic/notification/clock binding. Supplying a broker without these dependencies fails; a scoped LiveExecutionGuard without an active Risk enforcer fails. Omitted parameters preserve original Live broker construction, Guard, symbol validator, pending tracker, forensic output and notification path.
- A network-denied test sends one mechanical order through existing order validation and a locally scoped LiveExecutionGuard to SimulatedBrokerAdapter, with local ledger and pending state. The service made one local broker placement and no network request. Expanded applicable regression **173 passed / 0 failed**; four protected persistence hashes unchanged.
- This does **not** yet prove canonical queued-owner-to-service wiring or equivalent RiskEnforcement with full position/reconciliation state. The service currently calls Guard evaluation both before and during `authorize_and_send`; counted Risk invocations may exceed one, though only one local placement occurred. Missing-SL/TP enhancement and other service fallbacks still need explicit scoping or a proven unreachable-path argument. Baseline forbidden.

## G-forensics — queued-owner delivery ordering

- Start `a34e880`; production/config changes: none. A focused network-free test exercises the existing `_opportunity_processing_loop` with two equal-event-time intents and reverses their delivery order. The first processed symbol reverses too. The worker checks every 0.1 wall-clock seconds, and its recent-symbol/count state and five-minute reset are local to the worker loop. This is a source-and-test-proven scheduling sensitivity, not proof that historical orders were duplicated or that a particular historical queue order occurred.
- Replay must not silently impose a deterministic multi-intent order and claim full Live queue parity. Neither the historical delivery/batch schedule nor its tie ordering is recorded in the inspected contract. The existing single-intent queue subset remains independently investigable, but full multi-intent historical parity and an economic baseline remain gated. No queue semantics were changed.
- Correlation snapshot pinning and deterministic replay publication remain separately verified; historical Live correlation wake-ups remain unreconstructable. XMR root cause and broker retry semantics remain unresolved.

## Edge-measurement readiness audit — focus lock

- Start `0d557ba`; documentation-only `EDGE_MEASUREMENT_READINESS_AUDIT.md` and `PROJECT_DECISION_LEDGER.md`. Lynxion remains the platform; no framework migration, strategy/Risk/Fusion/cost policy change, research branch or baseline.
- Correlation snapshot contract rechecked against current source and tests; 19 focused causal/scope/correlation/queue tests passed. Four protected production persistence hashes matched before/after. No authenticated broker/network activity.
- Level 1 pre-queue signal research can exclude portfolio sizing/correlation **only if** its question and outcome are explicitly bounded; Level 2 cannot. Full decision trace, reached event-time semantics, decision-prefix invariance and after-cost outcome model remain unproven. `EDGE_MEASUREMENT_NOT_READY`; next unit is trace/evidence on existing canonical handlers, not broad ApplicationRunScope polish.

## Level-1 trace slice — existing canonical events only

- Start `8fcd179`; `ReplayDecisionRunScope` now records read-only normalized event payloads before routing; normalization includes all dataclass/metadata/risk fields and fails on unknown values. Only random `ExecutionIntent.intent_id` is omitted from this *signal-decision* trace; claim/duplicate parity remains separate. No strategy/Fusion/Risk/order policy changed.
- A closed-bar fixture repeats and is prefix-stable through MarketObservation, InterpretedSignal and FusedSignal. It produces **no ExecutionIntent**, so this is not the full decision-prefix gate. The test denies socket connections and observes no attempts in this fixture, but source audit finds `BaseStrategyAdapter.ensure_data_buffer` still resolves the global broker registry with `download_enabled=True`; therefore the research composition is not structurally network-incapable or point-in-time-history safe yet. No baseline or edge verdict.
- Expanded relevant regressions: **61 passed / 0 failed**, 26 warnings. Four protected production persistence SHA-256 hashes matched immediately before/after. Next blocker: narrow causal historical-provider binding for reached strategies, plus explicit symbol/timeframe buffer semantics, before asking this fixture to produce a canonical intent.

## Strategy historical-data dependency seam

- Start `8c7ee54`; production file `strategy_adapters.py` gains optional explicit history-loader binding. Omitted Live behavior still uses the same settings/registry/download-capable provider. When bound, an empty source result cannot fall through to that global path. `ReplayDecisionRunScope` binds a fail-closed empty source to every registered adapter until a validated point-in-time source exists; it does not fabricate bars or force an intent.
- Tests verify the explicit path does not call the global registry, default Live still calls it with `download_enabled=True`, and the scoped canonical event path uses no registry lookup. Expanded relevant regressions **66 passed / 0 failed**. Protected persistence hashes unchanged before/after; no authenticated broker/network request. This closes one hidden external dependency, **not** the strategy-history/MTF or cross-symbol state gate.

## One-symbol causal strategy-history feed

- Start `703e816`; new `CausalStrategyHistoryFeed` calls existing `BaseStrategyAdapter.update_with_market_data` for actual completed bars with **exact** configured timeframe, one declared symbol, and no rolling proxy. `ClosedBarDecisionDriver` may accept this feed. At a shared close timestamp, all actually completed timeframe bars enter their respective buffers before either observation is evaluated; later bars are not preloaded. Default driver construction remains unchanged.
- Tests reject cross-symbol/future/duplicate history, verify exact 1m/1h alignment and same-close availability, and compare normalized canonical event trace with/without appended future data. The two-bar fixture still emits **no ExecutionIntent**; this is not full signal-prefix or Live/replay parity. Expanded relevant regressions **69 passed / 0 failed**, 26 warnings; four protected persistence hashes unchanged before/after; no broker/network activity. Multi-symbol adapter buffers and strategy-specific higher-timeframe archive coverage remain open.

## Strategy input provenance — bounded source audit

- Start `a45bf47`; documentation-only `STRATEGY_INPUT_PROVENANCE_GAP.md` and readiness/decision-ledger updates. `SetupEngine` uses wall-clock setup timestamps; shared `DecisionPipeline` substitutes direction-favoring OBI/CVD values and synthetic bid/ask around close when these microstructure inputs are absent. Default setup-based adapters call that pipeline, so candle-only history alone cannot validate after-cost entry behavior. The frozen two-bar fixture did not produce an intent; actual fallback consumption in historical orders is **not** claimed.
- No strategy or trading-policy edit, data invention, profitability run or network/broker action. The preceding 69-test regression and protected hashes remain the latest executed evidence. `EDGE_MEASUREMENT_NOT_READY`; smallest next proof is point-in-time strategy input coverage and a reached intent-level/event-time/prefix trace, or an explicitly preregistered narrower pre-intent signal question. XMR/broker retry statuses unchanged.

## Local microstructure archive schema check

- Start `c127d18`; documentation-only extension to input gap and decision ledger. Inspected compressed CSV headers and source manifests read-only, without calculating outcomes or changing frozen research. Bookdepth has depth/notional bands, taker-flow has minute OHLC/volume/taker-buy volume, and BTC aggregate trades have minute volume/imbalance. None of the inspected normalized headers directly supplies per-decision `obi_ratio`, `cvd`, `best_bid` and `best_ask` together. Do not treat derived proxies as the same fields without a separately approved contract.
- No test rerun, production/research file mutation or network/broker action. Existing 69-pass regression and persistence hash evidence remain the latest. The source-input blocker is not cleared; baseline stays forbidden.

## Pre-intent signal readiness and microstructure contract — bounded unit

- Start `3c16b9e`; selected only the existing closed-bar watcher → routed Engine → single-input Fusion output as a potential Level-1 predictive-signal research boundary. Frozen a pre-outcome protocol in `PRE_INTENT_SIGNAL_STUDY_PREREGISTRATION.md`; **not activated**, no forward labels or economic results computed.
- New six-bar/two-symbol fresh-scope fixture verifies repeated normalized routed output and prefix T versus T+future through actual Engine/Fusion events. Expanded relevant regression **12 passed / 0 failed**. This is fixture-level evidence, not a qualified historical-archive prefix gate. No production source or trading policy changed.
- Local 1h BTC/ETH processed CSV timestamp/source semantics remain unverified and their apparent common interval is about 34 hours, below the frozen 20-days-per-symbol requirement. Thus `PRE_INTENT_EDGE_MEASUREMENT_NOT_READY`. Full Strategy/ExecutionIntent path remains blocked by point-in-time OBI/CVD/BBO provenance, wall-clock setup timestamps and other prior gates. Exact field/fallback matrix is in `PRE_INTENT_SIGNAL_READINESS_AND_MICROSTRUCTURE_AUDIT.md`.
- Four protected production persistence hashes equal the prior recorded values; no authenticated network/broker activity. XMR root cause and broker retry remain unresolved. Next action: qualify a continuous causal candle archive with unambiguous close-time and sufficient frozen-cohort coverage, then run historical-data prefix/determinism before any outcome study; separately identify an actual point-in-time microstructure feed for the full strategy gate.

## Frozen pre-intent candle archive qualification

- Start `aa1b136`; documentation-only read-only inventory and full-row quality scan of 12 BTC/ETH raw, processed and micro candle files. No frozen protocol, data or production code changed. Evidence: `HISTORICAL_CANDLE_PROVENANCE_AND_COVERAGE_QUALIFICATION.md`.
- Frozen processed 1h BTC/ETH files individually have 721/722 contiguous valid OHLCV rows, but only **34 overlapping rows**, shorter than the 50-bar warmup and 20 UTC days per symbol. Their particular file lineage/open-close timestamp contract is not proven by a per-file manifest; unrelated loader provenance says only `CSV`. Other micro files cannot replace the explicitly named cohort.
- `PRE_INTENT_EDGE_MEASUREMENT_NOT_READY`; `REAL_ARCHIVE_PREFIX_INVARIANCE_NOT_TESTABLE`. No real-archive prefix run, future label or Edge outcome was calculated. The previously passing fixture tests were not rerun because no decision code changed. Protected production persistence hashes remained unchanged; no network/broker activity. Full Strategy synthetic-fallback and SetupEngine clock findings remain separate and unremediated.

## Frozen dataset resolution and acquisition contract

- Start `5a8cdea`; verified preregistration SHA-256 `454485ff11fad12a9ad355517d3c1461b1df1676e182937c6c2d7e02d10a8cac` before inspecting candidates. Exact protocol requires the common intersection of the two named processed 1h BTC/ETH files, 50-bar warmup, >=100 non-overlapping eligible primary events and >=20 distinct UTC days per symbol—not an independently chosen 20-day window for each file, nor literally 20 full 24-hour days.
- Read-only source/coverage resolution reconfirmed unchanged file hashes and only 34 shared bars. No timestamp/exchange lineage proof for those exact files. Result `PRE_INTENT_DATASET_NOT_AVAILABLE`; no real-archive prefix run or outcome computation. `PRE_INTENT_DATASET_RESOLUTION_AND_ACQUISITION_SPEC.md` gives a non-executed single-source acquisition/immutable-manifest plan and notes that a new dataset needs a separately frozen pre-outcome binding, not silent substitution.
- No production file, data or frozen research definition changed; protected persistence hashes unchanged, no authenticated network/broker activity. Independent Strategy/SetupEngine/XMR/retry blockers remain parked.
