# Test record

`pytest -q tests/unit/test_historical_closed_bar_source.py --disable-warnings --tb=short`: 5 passed, 0 failed. Covered completed-bar gating, source-prefix equality, duplicate/gap/order rejection, MTF close boundary, NaN rejection, repeated construction and UTC day boundary.

Not run: full canonical-path test, live/replay parity, risk/guard parity, normalized decision trace, network-capable broker test, profitability/backtest. No authenticated exchange request was made by the tests. This result is insufficient for G1/G5/G6/G8/G9 at decision level.
