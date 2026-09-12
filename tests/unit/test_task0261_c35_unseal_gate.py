import pytest

from scripts.check_c35_unseal_gate import check, check_verified


def _events(total=240, long_count=120, weeks=8, symbols=6):
    events = []
    for index in range(total):
        key = f"S{index % symbols}:{index}"
        events.append({"kind": "SIGNAL", "signal_key": key})
        events.append({
            "kind": "OUTCOME",
            "signal_key": key,
            "status": "COMPLETE",
            "side": "LONG" if index < long_count else "SHORT",
            "symbol": f"S{index % symbols}",
            "exit_open_time": 1789088400 + (index % weeks) * 7 * 86400,
        })
    return events


def test_seals_empty_cohort_without_economic_fields():
    result = check([])
    assert result["aggregate_economics"] == "SEALED"
    assert result["verdict"] == "COLLECTING"
    assert not any("return" in key or "expectancy" in key for key in result)


def test_opens_only_when_all_minimum_coverage_gates_pass():
    result = check(_events())
    assert result["aggregate_economics"] == "READY_FOR_FROZEN_EVALUATION"
    assert all(result["minimum_gates"].values())


def test_each_coverage_dimension_fails_closed():
    assert check(_events(total=239))["aggregate_economics"] == "SEALED"
    assert check(_events(long_count=79))["aggregate_economics"] == "SEALED"
    assert check(_events(weeks=7))["aggregate_economics"] == "SEALED"
    assert check(_events(symbols=3))["aggregate_economics"] == "SEALED"


def test_rejects_orphan_or_duplicate_outcomes():
    orphan = [{"kind": "OUTCOME", "signal_key": "x", "status": "COMPLETE", "side": "LONG"}]
    try:
        check(orphan)
    except ValueError as exc:
        assert "orphan" in str(exc)
    else:
        raise AssertionError("orphan outcome accepted")


def test_verified_gate_rejects_coverage_shaped_but_unproven_events():
    with pytest.raises(ValueError, match="signal identity"):
        check_verified(_events())
