import importlib.util
from pathlib import Path

import pandas as pd


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_premium_basis_convergence_c20.py"
    spec = importlib.util.spec_from_file_location("edge_c20", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_uses_exact_completed_premium_candle_without_fill():
    evaluator = module(); base = evaluator._base()
    decisions = [base.DECISION_SECONDS * index for index in range(1, 183)]
    price = pd.DataFrame({"open": 100.0, "close": 100.0}, index=decisions)
    premium_timestamps = [decision - base.BAR_SECONDS for decision in decisions[:-1]]
    premium = pd.DataFrame({"close": 0.001}, index=premium_timestamps)

    features = evaluator.causal_features(price, premium)

    assert decisions[-1] not in features.index
    assert (features["snapshot_timestamp"] == features.index - base.BAR_SECONDS).all()


def test_score_direction_is_opposite_premium_for_convergence():
    evaluator = module(); base = evaluator._base()
    decision = base.DECISION_SECONDS
    price = pd.DataFrame({"open": [100.0], "close": [100.0]}, index=[decision])
    premium = pd.DataFrame({"close": [0.002]}, index=[decision - base.BAR_SECONDS])

    feature = evaluator.causal_features(price, premium).iloc[0]

    assert feature["premium_close"] > 0
    assert feature["imbalance"] < 0


def test_threshold_excludes_current_premium():
    evaluator = module(); base = evaluator._base()
    decisions = [base.DECISION_SECONDS * index for index in range(1, 183)]
    price = pd.DataFrame({"open": 100.0, "close": 100.0}, index=decisions)
    premium = pd.DataFrame({"close": [0.001] * 181 + [0.1]},
                           index=[decision - base.BAR_SECONDS for decision in decisions])

    features = evaluator.causal_features(price, premium)

    assert abs(features.iloc[-1]["threshold"] - 0.001) < 1e-12
