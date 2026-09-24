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

- Starting commit: `3da13d5`; resulting implementation commit recorded after commit creation.
- Production-source files changed: `infrastructure/messaging/event_system.py`, `infrastructure/watchers/adapters/historical_candle.py`, `infrastructure/aggregators/signal_aggregator.py`; new clock file `infrastructure/messaging/clock.py` and focused test `tests/unit/test_replay_event_time_scope.py`.
- Clock: injected `LiveClock` default / monotonic UTC `ReplayClock` for tested slice. State: fresh injected router, aggregator and selector in tests; full application state **not isolated**.
- Tests: 50 passed / 0 failed in the focused suite (see test-results addendum).
- Remaining wall clock: multi-signal Fusion, auto-detection execution/cooldown, and untraced strategy/adapter calls. Remaining globals: hierarchical Fusion, SignalProcessor container access, production claims/cooldowns/journals.
- Watcher limitation: unchanged Unit-1 matrix; no invented data.
- Network activity: NONE in focused tests. Production persistence mutation: NONE from new tests; no full replay was run.
