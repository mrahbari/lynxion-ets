import pandas as pd

from scripts.evaluate_funding_clock_market_quality import depth_before, flow_window, paired_record


def test_windows_are_strictly_backward_and_paired_against_control():
    timestamps = [900, 1800, 2700, 3600, 4500, 5400, 8100, 9000, 9900, 10800, 11700, 12600]
    flow = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0] * 12,
            "close": [101.0] * 12,
            "quote_volume": [100.0] * 12,
            "count": [10] * 12,
            "taker_buy_quote_volume": [60.0] * 12,
        }
    ).set_index("timestamp")
    depth = pd.DataFrame(
        {
            "timestamp": [3599, 6299, 10799, 13499],
            "notional_m1": [50.0] * 4,
            "notional_p1": [50.0] * 4,
        }
    ).set_index("timestamp")

    assert flow_window(flow, 3600) is not None
    result, reason = paired_record(flow, depth, 3600, 10800)
    assert reason is None
    assert result["log_quote_volume"] == 0.0
    assert result["depth_available"] is True


def test_depth_never_uses_snapshot_at_or_after_boundary():
    depth = pd.DataFrame(
        {"timestamp": [99, 100], "notional_m1": [10.0, 100.0], "notional_p1": [10.0, 100.0]}
    ).set_index("timestamp")

    assert depth_before(depth, 100)["depth_1pct"] == 20.0
