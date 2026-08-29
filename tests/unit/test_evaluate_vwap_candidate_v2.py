import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_vwap_candidate_v2.py"


def _module():
    spec = importlib.util.spec_from_file_location("evaluate_vwap_candidate_v2", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_chronological_folds_are_disjoint_and_cover_boundaries():
    module = _module()
    assert [module.chronological_fold(index, 8) for index in range(8)] == [1, 1, 2, 2, 3, 3, 4, 4]


def test_metrics_include_cost_adjusted_profit_factor_and_drawdown():
    result = _module().metrics([0.02, -0.01, -0.005, 0.01])
    assert result["n"] == 4
    assert result["expectancy"] == 0.00375
    assert result["profit_factor"] == 2.0
    assert result["win_rate"] == 0.5
    assert result["max_drawdown_return_units"] == 0.015


def test_regime_labels_do_not_change_when_future_bars_are_mutated():
    module = _module()
    original = pd.DataFrame({
        "close": [100 + index * 0.1 for index in range(160)],
        "high": [101 + index * 0.1 for index in range(160)],
        "low": [99 + index * 0.1 for index in range(160)],
    })
    altered = original.copy()
    altered.loc[120:, ["close", "high", "low"]] *= 10

    assert module.label_regimes(original)[:120] == module.label_regimes(altered)[:120]
