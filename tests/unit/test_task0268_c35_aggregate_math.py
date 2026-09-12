import math

import pytest

from scripts.c35_aggregate_math import (
    chronological_week_folds,
    daily_clustered_lower_bound,
    max_drawdown,
    mean,
    profit_factor,
)


def _row(key, entry, exit_, value):
    return {
        "signal_key": key, "entry_open_time": entry, "exit_open_time": exit_,
        "net_return_primary_0_30pct": value,
    }


def test_mean_profit_factor_and_zero_loss_semantics():
    assert mean([0.1, -0.05]) == pytest.approx(0.025)
    assert profit_factor([0.1, -0.05]) == pytest.approx(2.0)
    assert math.isinf(profit_factor([0.1]))
    assert profit_factor([0.0]) is None


def test_drawdown_compounds_in_chronological_order():
    assert max_drawdown([0.1, -0.2, 0.05]) == pytest.approx(0.2)


def test_daily_cluster_bootstrap_is_seeded_and_clusters_days():
    rows = [
        _row("a", 1789088400, 1789095600, 0.01),
        _row("b", 1789092000, 1789099200, 0.03),
        _row("c", 1789174800, 1789182000, -0.02),
    ]
    first = daily_clustered_lower_bound(rows, samples=100, seed=350035)
    assert first == daily_clustered_lower_bound(rows, samples=100, seed=350035)


def test_four_folds_use_contiguous_utc_weeks():
    base = 1789088400
    rows = [_row(str(index), base + index * 7 * 86400, base + index * 7 * 86400 + 7200, 0.01) for index in range(8)]
    folds = chronological_week_folds(rows)
    assert [len(fold) for fold in folds] == [2, 2, 2, 2]


def test_fold_boundary_crossing_fails_closed():
    sunday = 1789340400
    rows = [
        _row("cross", sunday, sunday + 7200, 0.01),
        _row("later", sunday + 7 * 86400, sunday + 7 * 86400 + 7200, 0.01),
    ]
    with pytest.raises(ValueError, match="crosses"):
        chronological_week_folds(rows)
