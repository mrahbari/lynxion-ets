"""A failed open-order query must never be read as 'no stop' (no duplicate/UNKNOWN stop attach).

Live VST 2026-11-22: after a restart the manager treated failed snapshots as missing stops for
AAVE/M/PAXG/AVAX, re-attached stops 38 times and left four PROTECTION_UNKNOWN journal rows.
"""
import infrastructure.risk.active_position_manager as mod


def test_stop_attach_requires_an_ok_open_order_snapshot():
    src = open(mod.__file__).read()
    assert 'evidence.get("status") != "OK"' in src
    assert "raise _SnapshotUnavailable()" in src and "except _SnapshotUnavailable:" in src
    assert issubclass(mod._SnapshotUnavailable, Exception)
