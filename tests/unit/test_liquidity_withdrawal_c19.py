import importlib.util
from pathlib import Path

import pandas as pd


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_liquidity_withdrawal_c19.py"
    spec = importlib.util.spec_from_file_location("edge_c19", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_uses_strict_current_and_four_hour_lag_snapshots():
    evaluator = module(); base = evaluator._base()
    decisions = [base.DECISION_SECONDS * index for index in range(2, 184)]
    price = pd.DataFrame({"open": 100.0, "close": 100.0}, index=decisions)
    anchors = sorted({timestamp - 1 for decision in decisions
                      for timestamp in (decision, decision - base.DECISION_SECONDS)})
    book = pd.DataFrame({"notional_m1": 60.0, "notional_p1": 40.0}, index=anchors)

    features = evaluator.causal_features(price, book)

    assert (features["snapshot_timestamp"] < features.index).all()
    assert (features["lag_snapshot_timestamp"] < features.index - base.DECISION_SECONDS).all()
    assert features["book_age_seconds"].max() <= base.MAX_BOOK_AGE


def test_positive_score_means_ask_withdrawal_relative_to_bid():
    evaluator = module(); base = evaluator._base()
    decision = 2 * base.DECISION_SECONDS
    price = pd.DataFrame({"open": [100.0], "close": [100.0]}, index=[decision])
    book = pd.DataFrame({"notional_m1": [100.0, 100.0], "notional_p1": [100.0, 50.0]},
                        index=[decision - base.DECISION_SECONDS - 1, decision - 1])

    feature = evaluator.causal_features(price, book).iloc[0]

    assert feature["imbalance"] > 0
    assert abs(feature["imbalance"] - float(evaluator.np.log(2))) < 1e-12


def test_report_identity_is_c19(monkeypatch):
    evaluator = module(); base = evaluator._base()
    monkeypatch.setattr(base, "build_report", lambda *_: {"candidate": "C-18", "protocol": "old"})
    monkeypatch.setattr(evaluator, "_base", lambda: base)

    report = evaluator.build_report(Path(), Path(), Path())

    assert report == {"candidate": "C-19", "protocol": "edge-candidate-register-v18"}
