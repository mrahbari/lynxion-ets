import pandas as pd

from scripts.explore_a1_mean_reversion_flow import metrics, profit_factor


def frame(values):
    return pd.DataFrame({"net_return": values, "entry_day": ["2026-01-01"] * len(values)})


def test_metrics_report_net_expectancy_profit_factor_and_clusters():
    result = metrics(frame([0.02, -0.01, 0.01]))
    assert result["n"] == 3
    assert result["day_clusters"] == 1
    assert result["expectancy"] == 0.02 / 3
    assert result["profit_factor"] == 3.0
    assert result["win_rate"] == 2 / 3


def test_profit_factor_handles_no_losses_without_nan():
    assert profit_factor(pd.Series([0.01, 0.02])) == float("inf")
    assert profit_factor(pd.Series([0.0])) is None
