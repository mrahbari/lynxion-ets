# Test record

`pytest -q tests/unit/test_historical_closed_bar_source.py --disable-warnings --tb=short`: 5 passed, 0 failed. Covered completed-bar gating, source-prefix equality, duplicate/gap/order rejection, MTF close boundary, NaN rejection, repeated construction and UTC day boundary.

Not run: full canonical-path test, live/replay parity, risk/guard parity, normalized decision trace, network-capable broker test, profitability/backtest. No authenticated exchange request was made by the tests. This result is insufficient for G1/G5/G6/G8/G9 at decision level.

## Unit 2 addendum

`pytest -q tests/unit/test_replay_event_time_scope.py tests/unit/test_historical_closed_bar_source.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_f01_offline_intent_sizing.py --disable-warnings --tb=short`: **50 passed, 0 failed**, 26 warnings. T1/T2 typed event and historical watcher time: covered for supplied close time; T3/T4 synchronous same-method aggregation: covered; T5/T6 isolated aggregator/router/subscriptions: covered; T7 production persistence: only the tested scope contains no persistence dependency, full application not covered; T8 repeat intermediate selected symbols: covered; T9/T10 focused prior tests: passed. No sleep/wait race or network-capable broker in new tests. Full application state, decision prefix invariance and live/replay parity remain untested.

## Unit 3 architectural stop

No Unit-3 code was changed and no Unit-3 tests were added or run. T1–T10 (full per-run composition, risk/claim/persistence isolation and wall-clock independence) are **NOT TESTABLE** safely with the current graph. Unit-1/2/ownership test results above remain historical evidence, not fresh Unit-3 verification. Four production persistence files were hashed read-only before and after the document-only audit; compare the Unit-3 manifest. No replay or broker was constructed.

## Implementation A pre-edit stop

T1–T11 were **NOT RUN**. Source inspection found a material price-contract mismatch before editing; see `IMPLEMENTATION_A_SIGNAL_PROCESSOR_SEAM.md`. No implementation test pass, production-persistence before/after test claim, prefix-invariance pass, or live/replay parity claim is made. No broker/network action occurred in this inspection.

## Autonomous program A-partial

`pytest -q tests/unit/test_signal_processor_forensic_seam.py tests/unit/test_replay_event_time_scope.py tests/unit/test_historical_closed_bar_source.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py --disable-warnings --tb=short`: **46 passed, 0 failed**, 26 warnings. Explicit forensic sink and default singleton identity were directly tested. Price-recorder T1–T4 and full replay/parity were not tested. No broker was instantiated by the new tests.

## Autonomous program B

`pytest -q tests/unit/test_fusion_instance_seam.py tests/unit/test_anomaly_signal_consistency.py tests/unit/test_signal_processor_forensic_seam.py tests/unit/test_replay_event_time_scope.py tests/unit/test_historical_closed_bar_source.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py --disable-warnings --tb=short`: **52 passed, 0 failed**. Covers scoped Fusion state/clock and prior focused slices only. Full decision-prefix and live/replay parity remain NOT TESTABLE.

## Autonomous program C

`pytest -q tests/unit/test_strategy_instance_scope.py --disable-warnings --tb=short`: **2 passed, 0 failed**. Fresh manager/adapter state and registration isolation only; no strategy-signal or intent parity assertion.

## Autonomous program D1

`pytest -q tests/unit/test_risk_enforcement_state_seam.py tests/unit/test_f01_offline_intent_sizing.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_historical_closed_bar_source.py --disable-warnings --tb=short`: **48 passed, 0 failed**, 4 warnings. Covers explicit temporary RiskEnforcement journal/gate seam, F01 and execution-path regression slices. Full risk/persistence isolation remains unproven.

## Autonomous program E1

`pytest -q tests/unit/test_intent_claim_scope.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_f01_offline_intent_sizing.py --disable-warnings --tb=short`: **45 passed, 0 failed**, 26 warnings. Atomic concurrent claim, independent explicit stores, shared live default and existing ownership/F01 slices. No exchange-level exactly-once or restart claim.

## Autonomous program D2

`pytest -q tests/unit/test_cooldown_event_clock_seam.py tests/unit/test_risk_enforcement_state_seam.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py --disable-warnings --tb=short`: **39 passed, 0 failed**, 26 warnings. Explicit event-time cooldown and prior risk/route slices; no full replay or parity test.

## Combined program checkpoint

Combined all six new seam suites with Unit-1/2, F01, pending-tracker and path-integrity slices: **77 passed, 0 failed**, 26 warnings. Four protected production persistence SHA-256 values matched immediately before/after the combined run; see program log. No canonical replay, prefix-invariance, live/replay parity, or economic baseline test ran.

## Market-price contract / Implementation A completion

`pytest -q tests/unit/test_market_observation_price_contract.py tests/unit/test_signal_processor_forensic_seam.py tests/unit/test_replay_event_time_scope.py tests/unit/test_historical_closed_bar_source.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_f01_offline_intent_sizing.py --disable-warnings --tb=short`: **64 passed, 0 failed**, 26 warnings. Included explicit/absent/invalid price, analytical-value non-price, tick snapshot, injected recorder, live bridge identity, forensic and prior path regressions. Four protected persistence hashes matched before/after this run. P6 is not applicable yet: no candle-derived producer was classified eligible; P7 is covered at the tick/observation snapshot boundary, not full canonical prefix invariance. P8 source audit found no automatic price assignment in ambiguous producers.

## D3 reconciliation journal isolation

Initial 20-test run passed but a subsequent read showed the shared `sl_cooldown_journal.json` hash differed from the earlier recorded hash; attribution was not provable without an immediate pre-test snapshot. The existing B4 fixture was amended to isolate the global cooldown gate to temporary journal paths. Repeating `test_reconciliation_journal_scope.py`, `test_b4_broker_reconciliation.py`, and `test_task0148_disconnected_exit_chain.py` then gave **20 passed, 0 failed**, 26 warnings, with all four protected persistence hashes identical immediately before/after. The altered shared journal was not reset or deleted.

## E2 pending-order state

`pytest -q tests/unit/test_pending_orders_tracker.py tests/unit/test_pending_orders_scope.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_intent_claim_scope.py --disable-warnings --tb=short`: **50 passed, 0 failed**, 26 warnings. Four protected production persistence hashes were identical immediately before/after. Live facade and two event-clock-owned states tested; broker-service injection remains untested/unimplemented.

## Final hard-stop regression checkpoint

Combined all current scoped price/forensic/Fusion/Strategy/Risk/claim/cooldown/reconciliation/pending tests with Unit-1/2, F01 and path-integrity slices: **111 passed, 0 failed**, 26 warnings. Four protected production persistence hashes were identical immediately before/after this run. Risk correlation worker timing was audited from source, not changed or simulated. Full canonical prefix invariance, live/replay parity and baseline remain NOT TESTABLE.

## Risk correlation scheduling source-forensic unit

`pytest -q tests/unit/test_risk_correlation_scheduling_forensics.py tests/unit/test_market_observation_price_contract.py tests/unit/test_signal_processor_forensic_seam.py tests/unit/test_fusion_instance_seam.py tests/unit/test_strategy_instance_scope.py tests/unit/test_risk_enforcement_state_seam.py tests/unit/test_cooldown_event_clock_seam.py tests/unit/test_intent_claim_scope.py tests/unit/test_pending_orders_scope.py tests/unit/test_reconciliation_journal_scope.py tests/unit/test_replay_event_time_scope.py tests/unit/test_historical_closed_bar_source.py tests/unit/test_f01_offline_intent_sizing.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py --disable-warnings --tb=short`: **84 passed, 0 failed**. The three new tests defer the worker thread, exercise the unchanged correlation calculation, and prove old-versus-new matrix interleaving changes quantity. They do not assert live scheduling parity. The four protected production persistence files had identical SHA-256 hashes immediately before/after. No broker/network activity. Earlier 111-test checkpoint is historical; this command is a focused subset plus new tests, not a repeat of the same full collection.

Expanded command adding `test_b4_broker_reconciliation.py`, `test_task0148_disconnected_exit_chain.py`, `test_anomaly_signal_consistency.py`, and `test_pending_orders_tracker.py`: **114 passed, 0 failed**. This covers the applicable prior 111-test slice plus three new correlation-characterization cases. Protected persistence hashes remained unchanged after this expanded run. No live broker/network adapter was constructed.

## F-prep orchestrator binding seam

`pytest -q tests/unit/test_architecture_orchestrator_scope_seam.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_replay_event_time_scope.py tests/unit/test_market_observation_price_contract.py tests/unit/test_signal_processor_forensic_seam.py --disable-warnings --tb=short`: **56 passed, 0 failed**. Default live identities, explicit router isolation and mismatched-router rejection covered. This does not exercise `ArchitectureOrchestrator.start/stop` in replay; global side effects there remain open. An expanded 20-file collection including prior 114 applicable cases and these three new cases returned **117 passed, 0 failed**, 26 warnings, with all four protected persistence hashes identical immediately before/after.

After explicit legacy-global ownership was added, `test_architecture_orchestrator_scope_seam.py` gave **4 passed / 0 failed**. The expanded 20-file collection gave **118 passed / 0 failed**, 26 warnings. It covers a scoped start/stop that cannot publish to the global orchestrator or clear the live pending tracker; it does not prove a complete ReplayScope. Four protected persistence hashes matched immediately before/after this expanded run.
