# Test record

`pytest -q tests/unit/test_historical_closed_bar_source.py --disable-warnings --tb=short`: 5 passed, 0 failed. Covered completed-bar gating, source-prefix equality, duplicate/gap/order rejection, MTF close boundary, NaN rejection, repeated construction and UTC day boundary.

Not run: full canonical-path test, live/replay parity, risk/guard parity, normalized decision trace, network-capable broker test, profitability/backtest. No authenticated exchange request was made by the tests. This result is insufficient for G1/G5/G6/G8/G9 at decision level.

## Unit 2 addendum

`pytest -q tests/unit/test_replay_event_time_scope.py tests/unit/test_historical_closed_bar_source.py tests/unit/test_path_integrity_unit1_routes.py tests/unit/test_path_integrity_unit3_runtime_wiring.py tests/unit/test_f01_offline_intent_sizing.py --disable-warnings --tb=short`: **50 passed, 0 failed**, 26 warnings. T1/T2 typed event and historical watcher time: covered for supplied close time; T3/T4 synchronous same-method aggregation: covered; T5/T6 isolated aggregator/router/subscriptions: covered; T7 production persistence: only the tested scope contains no persistence dependency, full application not covered; T8 repeat intermediate selected symbols: covered; T9/T10 focused prior tests: passed. No sleep/wait race or network-capable broker in new tests. Full application state, decision prefix invariance and live/replay parity remain untested.
