from infrastructure.risk.active_position_manager import ActivePositionManager


def test_stale_position_and_price_failures_are_terminal():
    messages = [
        "position not exist",
        "Position does not exist",
        "Stop Loss price should be lower than the current price",
        "stop price should be higher than current price",
        "position side mismatch",
    ]
    assert {
        ActivePositionManager._classify_stop_failure(message) for message in messages
    } == {"STALE_SNAPSHOT_TERMINAL"}


def test_timestamp_failure_is_the_only_retryable_class():
    assert ActivePositionManager._classify_stop_failure("timestamp is invalid") == (
        "TIMESTAMP_RETRYABLE"
    )
    assert ActivePositionManager._classify_stop_failure("timestamp expired") == (
        "TIMESTAMP_RETRYABLE"
    )


def test_unknown_or_empty_failure_is_ambiguous_terminal():
    assert ActivePositionManager._classify_stop_failure("rejected") == "AMBIGUOUS_TERMINAL"
    assert ActivePositionManager._classify_stop_failure(None) == "AMBIGUOUS_TERMINAL"
