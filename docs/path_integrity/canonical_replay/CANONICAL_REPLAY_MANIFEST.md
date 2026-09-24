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
