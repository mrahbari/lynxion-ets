import pandas as pd

from scripts.evaluate_lead_b_economic_holdout import (
    bootstrap_day_mean,
    build_trade,
    max_drawdown,
    profit_factor,
)


def test_trade_waits_for_observation_and_applies_funding_by_side():
    frame = pd.DataFrame(
        [
            {"price": 100.0, "quantity": 2.0, "transact_time": 0, "is_buyer_maker": False},
            {"price": 100.0, "quantity": 1.0, "transact_time": 5_000, "is_buyer_maker": True},
            {"price": 101.0, "quantity": 1.0, "transact_time": 10_000, "is_buyer_maker": False},
            {"price": 103.0, "quantity": 1.0, "transact_time": 43_200_000, "is_buyer_maker": True},
        ]
    )
    funding = pd.DataFrame([{"timestamp": 20_000, "funding_rate": 0.001}])

    trade, reason = build_trade(frame, 0, funding)

    assert reason is None
    assert trade["direction"] == "LONG"
    assert trade["entry_timestamp_ms"] == 10_000
    assert trade["gross_return"] == 103.0 / 101.0 - 1.0
    assert trade["funding_return"] == -0.001


def test_statistics_helpers_preserve_loss_sign_and_day_clusters():
    assert profit_factor([0.02, -0.01]) == 2.0
    assert max_drawdown([0.1, -0.2]) < -0.19
    frame = pd.DataFrame(
        {"day": ["a", "a", "b", "b"], "net": [0.01, 0.01, -0.01, -0.01]}
    )
    interval = bootstrap_day_mean(frame, "net", draws=100)
    assert interval[0] <= 0 <= interval[1]
