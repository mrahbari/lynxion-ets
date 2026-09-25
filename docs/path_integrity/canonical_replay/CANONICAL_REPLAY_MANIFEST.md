# Unit 1 manifest

- Starting commit: `87affd4`.
- Resulting implementation commit: `7fe30d7` (this manifest line was finalized afterward).
- Changed files: `infrastructure/replay/__init__.py`, `infrastructure/replay/historical_closed_bar_source.py`, `tests/unit/test_historical_closed_bar_source.py`, and the eight required documents in this directory. No production runtime file/config changed.
- Tests: focused source suite, 5 pass / 0 fail.
- Fixture identity: `tests/unit/test_historical_closed_bar_source.py`; SHA-256 `68ac84d4c9283d95722039ac99925a2e9de16b0b19e3d5eec61269c0a7b446c5`.
- Source identity: SHA-256 `7c29b5a2948e49bf077bf1837996d511ffdfbc749dd58d6b690f91b93454b46c`.
- Configuration identity: none loaded by the isolated source tests; no equivalence to production configuration claimed.
- Remaining UNKNOWNs: live watcher replayability, event-time clock, aggregator scheduling, per-run state isolation, Risk/Guard/simulated broker parity, normalized decision trace, broker timeout/restart semantics.
- Legacy backtest: unchanged, `LEGACY_NONCANONICAL`; no PnL used.
- Broker network requests: zero by the new source/tests; no broker adapter imported or constructed.
- Pre-existing C-11/C-35 working-tree changes were not staged or modified by this unit.

## Unit 2 addendum

- Starting commit: `3da13d5`; resulting Unit-2 implementation commit: `e84dcdf` (manifest finalized afterward).
- Production-source files changed: `infrastructure/messaging/event_system.py`, `infrastructure/watchers/adapters/historical_candle.py`, `infrastructure/aggregators/signal_aggregator.py`; new clock file `infrastructure/messaging/clock.py` and focused test `tests/unit/test_replay_event_time_scope.py`.
- Clock: injected `LiveClock` default / monotonic UTC `ReplayClock` for tested slice. State: fresh injected router, aggregator and selector in tests; full application state **not isolated**.
- Tests: 50 passed / 0 failed in the focused suite (see test-results addendum).
- Remaining wall clock: multi-signal Fusion, auto-detection execution/cooldown, and untraced strategy/adapter calls. Remaining globals: hierarchical Fusion, SignalProcessor container access, production claims/cooldowns/journals.
- Watcher limitation: unchanged Unit-1 matrix; no invented data.
- Network activity: NONE in focused tests. Production persistence mutation: NONE from new tests; no full replay was run.

## Unit 3 architectural-stop addendum

- Starting commit: `8016007`; resulting Unit-3 report commit: `0f950b1` (manifest finalized afterward). This is a documentation-only architectural stop, with no production implementation.
- Files changed: Unit-3 report, application-state matrix, persistence matrix, this manifest, event-time matrix and test-results addendum. Production files changed: NONE. Tests added/executed: NONE; pass/fail count: not applicable.
- Per-run components proven so far: only Unit-2's router/aggregator/clock slice. Full application context: NOT CONSTRUCTED.
- Remaining globals: container risk engine, forensic logger, hierarchical Fusion, strategy defaults/nested dependencies, auto-detection class-level claims, cooldown gate, pending tracker and persistence.
- Remaining wall-clock dependencies: multi-signal/neutral Fusion, state-machine transitions, strategy intent timestamps, cooldown/admission and pre-broker execution.
- Production persistence SHA-256 **before and after** audit matched: `active_positions_journal.json=11107b33a93f7d616abc1009ce41fdba955cacb422236643d97414f14033e1ab`; `live_order_journal.json=e72c03f35a18cd0732b97b901bff480977760bfebc4de603c9abb860e170f348`; `sl_cooldown_journal.json=d585dce9a5772ef78b512c395ac2fb5b4681cc64fc0ac69593bc831966987bfa`; `trade_journal.csv=1eb076e61351de3f0cd9f4fda81493e12bdd1588f82b6e114b8c48993cda0d14`. This proves no change to these four files during the read-only audit, not future replay safety.
- Network activity: NONE. Watcher limitations: unchanged. Remaining UNKNOWNs: exact safe persistence ports, all nested adapter state, event-time semantics downstream, full parity.

## Implementation A pre-edit architecture stop

- Starting HEAD: `fdeaa7a`. Result: documentation-only mismatch record; no implementation commit or production/config changes.
- Changed files: `IMPLEMENTATION_A_SIGNAL_PROCESSOR_SEAM.md`, this manifest, and `CANONICAL_REPLAY_TEST_RESULTS.md` only.
- Source inspected: `infrastructure/messaging/event_system.py`, `domain/entities/signal.py`, watcher constructors, `bootstrap/lifecycle.py`, `bootstrap/container.py`, architecture sequence. No new interface/adapter was created.
- Tests added/executed: NONE; pass/fail count: not applicable. The T1–T11 requested suite remains pending review of the observation-price contract.
- Production persistence hash comparison: NOT PERFORMED (no focused tests or production state writes were attempted); no claim of A-G5 verification.
- Network activity: NONE. Remaining globals: container risk lookup and forensic logger in SignalProcessor, plus previously documented globals; no seam was implemented.
- Remaining units: Implementation A after contract review, then separately authorized later architecture units. XMR: `XMR_ROOT_CAUSE_UNRESOLVED`. Prefix invariance and live/replay parity: `NOT_TESTABLE`.

## Autonomous program A-partial addendum

- Starting commit `c8e8bda`; this bounded unit adds only optional forensic-sink injection in `infrastructure/messaging/event_system.py`, a focused test, and documentation. Live default forensic singleton identity is preserved. No price contract/recorder change was made.
- Focused tests: 46 passed / 0 failed; see test-results addendum. Protected production persistence SHA-256 after tests matches the Unit-3 values recorded above; no fresh pre-test snapshot was taken, so A-G5 is not fully established. No authenticated network action was undertaken in the new tests.
- Price contract: `PRICE_CONTRACT_OPERATOR_DECISION_REQUIRED`. A remains PARTIAL; B–G unimplemented. Prefix invariance and live/replay parity remain NOT TESTABLE. XMR and broker retry statuses unchanged.

## Autonomous program B addendum

- Starting commit `058f5ac`; bounded Fusion instance/clock injection in `fusion_service.py`, `hierarchical_fusion_service.py`, and `symbol_state_machine.py`, with focused isolation test and documentation. No Fusion policy change or live composition change.
- Tests: 52 passed / 0 failed (focused B plus relevant prior slices). New tests used no broker/network dependency. Protected production persistence hashes matched prior documented values after test, but no fresh before-test snapshot was made.
- Remaining: A price contract, C–G seams, full global/persistence isolation, decision prefix invariance, and live/replay parity. XMR and broker retry statuses unchanged.

## Autonomous program C addendum

- Starting commit `2c50834`; no production/config changes. Added only strategy instance-scope test and documentation. 2 passed / 0 failed. Fresh `StrategyManager()` construction is already available; full event-time/config binding remains unproven.
- No new broker/network dependency. Production persistence before/after hash: NOT COLLECTED for this tiny constructor test; do not upgrade G7/I. XMR and broker retry statuses unchanged.

## Autonomous program D1 addendum

- Starting commit `a21c0f9`; one production file modified (`risk_enforcement.py`) for optional cooldown journal path and supplied-gate use. One new test and documentation. Live defaults unchanged by construction; focused test result 48 passed / 0 failed.
- Post-test protected production persistence hashes matched the four values recorded in the Unit-3 addendum. No fresh pre-test snapshot was collected; do not claim full gate I. New tests used no broker/network client. D remains PARTIAL; XMR and broker retry statuses unchanged.

## Autonomous program E1 addendum

- Starting commit `199b26d`; two production files changed for optional instance-scoped atomic claim store with shared live default. One focused test plus documentation. 45 passed / 0 failed.
- New tests had no broker/network capability. Fresh production-persistence before/after hash: NOT COLLECTED; full E/state-isolation gate is not met. Broker timeout/restart and XMR root cause remain unresolved.

## Autonomous program D2 addendum

- Starting commit `f0f434a`; one production file changed for optional clock injection in `SymbolCooldownGate`, with temporary-path test and documentation. 39 passed / 0 failed. Live default remains `LiveClock`; cooldown policy untouched.
- No new broker/network dependency. Fresh full production-persistence before/after hash: NOT COLLECTED. D/E isolation and decision-level parity remain incomplete; XMR and broker retry statuses unchanged.

## Combined autonomous-program checkpoint

- Starting source baseline `c8e8bda`; bounded commits, in order: `058f5ac` (forensic sink), `2c50834` (Fusion state/clock), `a21c0f9` (StrategyManager construction test), `199b26d` (RiskEnforcement journal/gate), `f0f434a` (intent claim store), `3d9f801` (cooldown event clock). This checkpoint is documentation-only.
- Combined focused regression: 77 passed / 0 failed. The four protected production persistence files were hashed immediately before and after and were unchanged. No authenticated broker access/order; no replay scope or baseline was run.
- Price contract requires decision; D/E are partial. `PREFIX_INVARIANCE_NOT_TESTABLE`; `LIVE_REPLAY_PARITY_NOT_TESTABLE`; `XMR_ROOT_CAUSE_UNRESOLVED`; `BROKER_RETRY_SEMANTICS_UNRESOLVED`.

## Operator-resolved price contract / A completion

- Starting commit `b95013d`; changed production files: `domain/entities/signal.py`, `infrastructure/messaging/event_system.py`, `infrastructure/watchers/adapters/tick.py`. New focused price-contract test and documentation. Old `observation.close`/silent inner swallow removed; optional explicit producer price and narrow recorder added.
- Focused tests: 64 passed / 0 failed. Protected persistence hashes before/after matched the Unit-3 values above. New tests used no broker/network client. A is VERIFIED for the seam; no full replay/decision parity was attempted.
- Price-contract blocker resolved by operator; producer uncertainty remains for candles/pulse/screener. D/E/F/G and A–K overall release gates remain incomplete. XMR and broker retry statuses unchanged.

## D3 reconciliation journal seam

- Starting commit `b5df2c2`; production file `broker_reconciliation.py` gains optional active-position journal path, preserving the live default. Added isolated-journal test; B4 test fixture now isolates the global cooldown gate to temporary files.
- Corrected focused run: 20 passed / 0 failed, four protected persistence hashes identical immediately before/after. An earlier run lacked a pre-test snapshot and was followed by a changed shared cooldown-journal hash; exact attribution is UNKNOWN. No data was reverted or deleted.
- New tests used fake broker objects, no authenticated broker request/order. D remains PARTIAL; full replay scope, prefix invariance, parity and economics are not authorized.

## E2 pending-order state addendum

- Starting commit `d894fb3`; shared tracker core and optional AutoDetection pending-state injection, with one new focused test and documentation. 50 passed / 0 failed. Protected persistence hashes identical before/after; no authenticated network/broker action.
- Live class facade and default remain process-wide. Broker services still use the live class directly; full E/F/G isolation remains incomplete. Prefix/parity/economic statuses unchanged.

## Final autonomous-program hard stop

- Starting commit `b95013d`; implementation commits `b5df2c2` (explicit market-price contract/A), `d894fb3` (reconciliation journal D3), `e622908` (pending state E2); this checkpoint is documentation-only.
- Production files changed after `b95013d`: `domain/entities/signal.py`, `infrastructure/messaging/event_system.py`, `infrastructure/watchers/adapters/tick.py`, `infrastructure/execution/broker_reconciliation.py`, `infrastructure/shared/pending_orders_tracker.py`, `infrastructure/orchestrators/auto_detection_orchestrator.py`. No strategy/Fusion/Risk numerical policy or broker order behavior intentionally changed.
- Final focused regression: 111 passed / 0 failed, 26 warnings; protected persistence hashes matched immediately before/after. No authenticated broker network request/order. See program log for an earlier cooldown-journal hash discrepancy without pre-test attribution.
- Hard stop: EnterpriseRiskManager wall-clock correlation worker changes the matrix consumed by risk-derived quantity; no source-proven event-time schedule preserves live decisions. `CANONICAL_REPLAY_BLOCKED_BY_POLICY_DECISION`; `PREFIX_INVARIANCE_NOT_TESTABLE`; `LIVE_REPLAY_PARITY_NOT_TESTABLE`; `XMR_ROOT_CAUSE_UNRESOLVED`; `BROKER_RETRY_SEMANTICS_UNRESOLVED`. Baseline NOT authorized.

## Risk correlation scheduling review addendum

- Starting HEAD `42b9985`; resulting documentation/test commit recorded by the next commit of this unit. Files added: `RISK_CORRELATION_SCHEDULING_AUDIT.md`, `RISK_CORRELATION_SCHEDULING_TRACE.csv`, `tests/unit/test_risk_correlation_scheduling_forensics.py`; existing program log/test results/manifest appended. Production source/config files changed: **0**.
- Current Live scheduling remains unchanged. Ordering of worker update versus sizing is decision-relevant and unrecorded. Status `CORRELATION_PARITY_BLOCKED_BY_LIVE_CONCURRENCY`. No replay scheduler or scope was built.
- Tests: 114 passed / 0 failed in the expanded focused collection (prior applicable 111 plus three new cases). Protected persistence SHA-256 values before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...` (all unchanged). Network/broker activity: NONE. C-35 DNS/public monitoring: not attempted; `C35_MONITORING_UNAVAILABLE_IN_CURRENT_ENVIRONMENT` is noncritical.
- Remaining: explicit Live/Replay ordering contract requires separate approval; full state/persistence isolation, watcher data, F/G, prefix invariance, live/replay parity, XMR cause and broker retry semantics unresolved. Economic baseline forbidden.

## F-prep scoped orchestrator binding addendum

- Start `892a57f`; resulting commit is this unit's commit. Production file changed: `infrastructure/orchestrators/architecture_orchestrator.py`; one test added. Optional binding of an explicit processor/aggregator preserves the same global live defaults. Mismatched explicit processor/router fails before subscriptions. Focused regression 56 passed / 0 failed; expanded applicable collection 117 passed / 0 failed, 26 warnings.
- Protected persistence hashes matched immediately before/after the expanded run: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. New tests used no broker/network adapter. This unit does **not** instantiate ReplayScope or eliminate import-time global router, `start()` global execution-service publication, or `stop()` global cleanup. Risk correlation parity remains blocked; economic baseline not authorized.

## F-prep legacy-global lifecycle ownership

- Start `fb25f9d`; resulting commit is this unit's commit. Production file `architecture_orchestrator.py` adds an optional ownership flag with the existing Live default unchanged. Explicit scoped instances can start/stop without publishing execution service into the global orchestrator or clearing global pending/broker-registry state. The scoped caller remains responsible for its own cleanup; no ReplayScope exists yet.
- Expanded regression **118 passed / 0 failed**, 26 warnings. Four protected persistence hashes matched immediately before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. New test uses no broker/network. Correlation parity and A–K release gates remain blocked/incomplete; baseline forbidden.

## Correlation snapshot consumption unit

- Start `ee569dd`; resulting commit is this unit's commit. Production files: `enterprise_risk_manager.py`, `risk_engine_adapter.py`. New test: `test_risk_correlation_snapshot_contract.py`. Immutable/versioned snapshots are published under the existing lock and pinned at dynamic-sizing entry. Live worker schedule, Risk formula, limits and strategy/Fusion behavior unchanged.
- Expanded local regression **125 passed / 0 failed**. Four protected persistence hashes matched immediately before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. Network/broker activity: NONE. Old historical publication schedule unavailable; replay scheduler and full scope not built. Baseline forbidden.

## Replay correlation scheduler unit

- Start `b153285`; resulting commit is this unit's commit. Production file `enterprise_risk_manager.py` adds optional worker startup; default Live worker remains enabled. New replay-only scheduler module and six tests. Replay anchor/tie rule documented in `REPLAY_CORRELATION_EVENT_TIME_CONTRACT.md`; no historical wake-up timing claim.
- Expanded local regression **131 passed / 0 failed**. Protected hashes before/after unchanged: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. No broker/network activity. Full ReplayScope and baseline not yet authorized.

## Queued-owner Risk/cooldown dependency addendum

- Start `3ecbdd7`; resulting commit is this unit's commit. Production files: `auto_detection_orchestrator.py`, `_auto_detection_execution.py`. One focused test file added. Explicit Risk-engine/cooldown-gate injection avoids those global lookups in the tested owner paths; default live paths remain.
- Expanded applicable regression **134 passed / 0 failed**. Protected persistence hashes unchanged before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. No authenticated broker/network activity. Constructor and full replay safety remain incomplete; no baseline.

## Queued-owner event-time addendum

- Start `d573cde`; resulting commit is this unit's commit. Production files: `auto_detection_orchestrator.py`, `_auto_detection_execution.py`, `_auto_detection_dedup.py`. Two tests added to the prior focused test file. Optional execution clock binds pending-intent, portfolio and order timestamps; omitted default retains LiveClock behavior. No policy/threshold change.
- Expanded regression **136 passed / 0 failed**. Protected persistence hashes unchanged before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. No authenticated broker/network activity. Remaining live heartbeat/price fallback/global constructor dependencies mean full scope and baseline remain blocked.

## Queued-owner constructor/teardown addendum

- Start `16c1659`; resulting commit is this unit's commit. Production file: `auto_detection_orchestrator.py`. One constructor/teardown test added. Optional explicit architecture/watcher/alert instances are used without changing default Live construction; scoped stop uses owned architecture and pending tracker. No trading policy or numerical control changed.
- Expanded regression **137 passed / 0 failed**. Protected persistence hashes identical before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. No authenticated network/broker activity. Full ApplicationRunScope, prefix/parity and economic baseline remain unavailable.

## Explicit execution-price source addendum

- Start `f772886`; resulting commit is this unit's commit. Production files: `auto_detection_orchestrator.py`, `_auto_detection_execution.py`. Four parametrized tests added. Explicit source has no fallback to live repository/exchange/synthetic price; invalid or unavailable price rejects before Risk/broker. Omitted source retains prior Live path. This is a source seam, not a replay runtime or Live policy change.
- Expanded regression **141 passed / 0 failed**. Protected hashes matched before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. No authenticated network/broker activity. A-K release gates incomplete; baseline forbidden.

## Scoped heartbeat event-time addendum

- Start `3e41773`; resulting commit is this unit's commit. Production files: `event_system.py`, `auto_detection_orchestrator.py`, `_auto_detection_execution.py`. Two focused tests added in existing files. Optional clock/source injection preserves Live defaults; explicit scoped source receives the same heartbeat freshness decision at event time.
- Expanded regression **143 passed / 0 failed**. Protected persistence hashes unchanged before/after: active `11107b33...`, live orders `e72c03f3...`, cooldown `0607bcea...`, trade `1eb076e6...`. No authenticated broker/network activity. Full ReplayScope, prefix/parity and baseline remain unavailable.
