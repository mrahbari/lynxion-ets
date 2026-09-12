import pytest

from scripts.update_c35_outcomes import _funding_covered, find_resolvable, verify_outcome_bindings


def _signal(exit_time=1789124400):
    return {
        "kind": "SIGNAL", "candidate": "C-35", "signal_key": "BTCUSDT:1789117200",
        "symbol": "BTCUSDT", "side": "LONG", "decision_time": 1789117200,
        "entry_open_time": 1789117200, "exit_open_time": exit_time,
    }


def _candles():
    return [{
        "symbol": "BTCUSDT", "open_time": 1789117200 + index * 900,
        "open": "100" if index < 8 else "102",
    } for index in range(9)]


def _coverage(end=1789124400000):
    return [{
        "symbol": "BTCUSDT", "status": "COMPLETE_PUBLIC_RESPONSE",
        "requested_start_ms": 1789087245000, "requested_end_ms": end,
    }]


def test_coverage_must_span_strict_post_entry_through_exit():
    assert _funding_covered(_coverage(), "BTCUSDT", 1789117200, 1789124400)
    assert not _funding_covered(_coverage(1789124399999), "BTCUSDT", 1789117200, 1789124400)


def test_resolves_only_mature_uniquely_supported_signal():
    outcomes = find_resolvable([_signal()], _candles(), [], _coverage())
    assert len(outcomes) == 1
    assert outcomes[0]["status"] == "COMPLETE"


def test_waits_for_exit_candle_or_funding_coverage():
    assert find_resolvable([_signal()], _candles()[:-1], [], _coverage()) == []
    assert find_resolvable([_signal()], _candles(), [], _coverage(1789124399999)) == []


def test_skips_already_completed_signal():
    events = [_signal(), {"kind": "OUTCOME", "signal_key": "BTCUSDT:1789117200"}]
    assert find_resolvable(events, _candles(), [], _coverage()) == []


def test_completed_outcome_is_recomputed_from_source_evidence():
    signal = _signal()
    outcome = find_resolvable([signal], _candles(), [], _coverage())[0]
    assert verify_outcome_bindings([signal, outcome], _candles(), [], _coverage())["integrity"] == "PASS"
    with pytest.raises(ValueError, match="differs from source evidence"):
        verify_outcome_bindings(
            [signal, {**outcome, "net_return_primary_0_30pct": 99.0}],
            _candles(), [], _coverage(),
        )


def test_completed_outcome_requires_persisting_funding_coverage():
    signal = _signal()
    outcome = find_resolvable([signal], _candles(), [], _coverage())[0]
    with pytest.raises(ValueError, match="lost complete funding coverage"):
        verify_outcome_bindings([signal, outcome], _candles(), [], [])
