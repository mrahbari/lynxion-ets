from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.research.exit_shadow_coverage_gate import shadow_coverage_gate


def records(count=100, activated=30, weeks=8, symbols=5, longs=50):
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    return [
        {
            "position_key": f"p{i}",
            "symbol": f"S{i % symbols}USDT",
            "side": "LONG" if i < longs else "SHORT",
            "terminal_time_utc": (start + timedelta(weeks=i % weeks)).isoformat(),
            "candidate_activated": i < activated,
        }
        for i in range(count)
    ]


def test_every_frozen_minimum_opens_aggregate_gate_only_at_once():
    result = shadow_coverage_gate(records())
    assert result["status"] == "READY_TO_OPEN_AGGREGATES"
    assert all(result["gates"].values())


@pytest.mark.parametrize("kwargs,gate", [
    ({"count": 99}, "paired_positions"),
    ({"activated": 29}, "activated_positions"),
    ({"weeks": 7}, "utc_weeks"),
    ({"symbols": 4}, "symbols"),
    ({"longs": 14}, "long_positions"),
    ({"longs": 86}, "short_positions"),
])
def test_each_minimum_independently_keeps_collecting(kwargs, gate):
    result = shadow_coverage_gate(records(**kwargs))
    assert result["status"] == "COLLECTING"
    assert result["gates"][gate] is False


def test_duplicate_identity_or_schema_drift_fails_closed():
    values = records(count=2, activated=1, weeks=1, symbols=1, longs=1)
    values[1]["position_key"] = values[0]["position_key"]
    with pytest.raises(ValueError, match="duplicated"):
        shadow_coverage_gate(values)
    value = records(count=1, activated=1, weeks=1, symbols=1, longs=1)[0]
    value["net_roe"] = 999.0
    with pytest.raises(ValueError, match="schema"):
        shadow_coverage_gate([value])


def test_non_utc_or_non_boolean_activation_fails_closed():
    value = records(count=1, activated=1, weeks=1, symbols=1, longs=1)[0]
    value["terminal_time_utc"] = "2026-01-05T00:00:00"
    with pytest.raises(ValueError, match="UTC"):
        shadow_coverage_gate([value])
    value["terminal_time_utc"] = "2026-01-05T00:00:00+00:00"
    value["candidate_activated"] = 1
    with pytest.raises(ValueError, match="invalid"):
        shadow_coverage_gate([value])
