# Test pollution of runtime state, 2026-11-22

These files were written by platform unit-test runs on 2026-11-22 between 11:56 and 12:13 UTC
(Claude session; three `pytest tests/unit` runs). All rows are synthetic test fixtures
(exchange UNKNOWN, order_id null, e.g. BTCUSDT stop_price 101.0; cooldown/loss history for
BTC/ETH/SOL/... at test-run timestamps). No platform runner was running; the epoch-1 journal had
been retired to empty at 00:34 the same day. The live files were reset to their retired-empty
state and `tests/conftest.py` now redirects all three paths to a temp dir.
