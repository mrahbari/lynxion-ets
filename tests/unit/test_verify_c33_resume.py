import copy

import pytest

from scripts.verify_c33_resume import verify_resume


def snapshots():
    before = {
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "activation_boundary": 1_788_500_000,
        "record_counts": {"heartbeat": 1_777, "kline_close": 10_686, "liquidation": 3_271, "session": 2},
        "session_count": 2,
        "active_session_count": 0,
        "latest_record_ms": 1_788_600_000_000,
        "eligible_completed_bucket_count": 351,
    }
    after = {
        **before,
        "record_counts": {"heartbeat": 1_782, "kline_close": 10_716, "liquidation": 3_271, "session": 3},
        "session_count": 3,
        "active_session_count": 1,
        "latest_record_ms": 1_788_600_300_001,
        "eligible_completed_bucket_count": 352,
    }
    return before, after


def test_valid_first_interval_resume_is_verified():
    before, after = snapshots()
    result = verify_resume(before, after)
    assert result["status"] == "RESUME_VERIFIED"
    assert result["record_count_increments"]["heartbeat"] == 5
    assert result["record_count_increments"]["kline_close"] == 30


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("active_session_count", 0, "exactly one active"),
        ("session_count", 4, "exactly one session"),
        ("eligible_completed_bucket_count", 350, "bucket count regressed"),
    ],
)
def test_resume_lifecycle_or_bucket_regression_fails_closed(field, value, message):
    before, after = snapshots()
    after[field] = value
    with pytest.raises(ValueError, match=message):
        verify_resume(before, after)


def test_any_record_counter_regression_fails_closed():
    before, after = snapshots()
    after["record_counts"]["liquidation"] = before["record_counts"]["liquidation"] - 1
    with pytest.raises(ValueError, match="liquidation record count regressed"):
        verify_resume(before, after)


@pytest.mark.parametrize(("record_type", "increment"), [("heartbeat", 4), ("kline_close", 29)])
def test_incomplete_first_interval_fails_closed(record_type, increment):
    before, after = snapshots()
    after = copy.deepcopy(after)
    after["record_counts"][record_type] = before["record_counts"][record_type] + increment
    with pytest.raises(ValueError, match="first complete interval"):
        verify_resume(before, after)
