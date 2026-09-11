import pytest

from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE
from scripts.verify_c35_candle_ledger import verify_rows


def _row(symbol, open_time):
    return {
        "symbol": symbol, "open_time": open_time, "close_time": open_time + 899,
        "open": "100", "high": "101", "low": "99", "close": "100.5", "volume": "12",
        "source_sha256": "a" * 64,
        "role": "PROSPECTIVE" if open_time > BOUNDARY_EPOCH else "WARMUP_ONLY",
    }


def _complete_rows():
    start = BOUNDARY_EPOCH - (BOUNDARY_EPOCH % 900)
    return [_row(symbol, timestamp) for symbol in UNIVERSE for timestamp in (start, start + 900)]


def test_accepts_complete_contiguous_strict_boundary_panel():
    report = verify_rows(_complete_rows())
    assert report["integrity"] == "PASS"
    assert report["prospective_records"] == len(UNIVERSE)


def test_rejects_duplicate_key():
    rows = _complete_rows()
    with pytest.raises(ValueError, match="duplicate"):
        verify_rows(rows + [rows[0]])


def test_rejects_gap():
    rows = _complete_rows()
    rows[1]["open_time"] += 900
    rows[1]["close_time"] += 900
    with pytest.raises(ValueError, match="non-contiguous"):
        verify_rows(rows)


def test_rejects_boundary_role_drift():
    rows = _complete_rows()
    rows[0]["role"] = "PROSPECTIVE"
    with pytest.raises(ValueError, match="boundary role"):
        verify_rows(rows)
