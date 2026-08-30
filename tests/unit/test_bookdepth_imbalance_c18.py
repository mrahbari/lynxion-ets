import importlib.util
from pathlib import Path

import pandas as pd


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_bookdepth_imbalance_c18.py"
    spec = importlib.util.spec_from_file_location("edge_c18", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_alignment_is_strictly_before_decision_and_bounded():
    evaluator = module()
    decisions = [evaluator.DECISION_SECONDS * index for index in range(1, 183)]
    price = pd.DataFrame({"open": 100, "close": 100}, index=decisions)
    timestamps = [timestamp - 1 for timestamp in decisions]
    timestamps[-1] = decisions[-1]
    book = pd.DataFrame({"notional_m1": 60.0, "notional_p1": 40.0}, index=timestamps)

    features = evaluator.causal_features(price, book)

    assert (features["snapshot_timestamp"] < features.index).all()
    assert decisions[-1] not in features.index
    assert features["book_age_seconds"].max() <= evaluator.MAX_BOOK_AGE


def test_threshold_excludes_current_observation():
    evaluator = module()
    decisions = [evaluator.DECISION_SECONDS * index for index in range(1, 183)]
    price = pd.DataFrame({"open": 100, "close": 100}, index=decisions)
    book = pd.DataFrame({"notional_m1": [55.0] * 181 + [99.0],
                         "notional_p1": [45.0] * 181 + [1.0]},
                        index=[timestamp - 1 for timestamp in decisions])

    features = evaluator.causal_features(price, book)

    assert abs(features.iloc[-1]["threshold"] - 0.10) < 1e-12


def test_collect_trade_uses_next_open_prior_bar_close_and_funding_sign(monkeypatch):
    evaluator = module()
    decision = evaluator.PRIMARY_START
    price = pd.DataFrame({"open": [100.0, 999.0], "close": [101.0, 110.0]},
                         index=[decision, decision + evaluator.EXIT_SECONDS - evaluator.BAR_SECONDS])
    features = pd.DataFrame({"snapshot_timestamp": [decision - 1], "book_age_seconds": [1],
                             "imbalance": [0.5], "threshold": [0.2]}, index=[decision])
    monkeypatch.setattr(evaluator, "causal_features", lambda *_: features)
    funding = pd.Series([0.001], index=[decision + 8 * 3600])

    trades, _ = evaluator.collect_trades("BTCUSDT", price, pd.DataFrame(), funding,
                                         decision, decision + evaluator.EXIT_SECONDS)

    assert trades[0]["entry_price"] == 100.0
    assert trades[0]["exit_price"] == 110.0
    assert abs(trades[0]["funding_return"] + 0.001) < 1e-12
    assert abs(trades[0]["gross_return"] - 0.099) < 1e-12


def test_primary_gate_requires_minimum_total_sample(monkeypatch):
    evaluator = module(); mechanics = evaluator._mechanics()
    trade = {"symbol": "BTCUSDT", "side": "LONG", "fold": 1,
             "decision_timestamp": evaluator.PRIMARY_START, "gross_return": 0.02,
             "price_pnl_return": 0.02, "funding_return": 0.0}
    monkeypatch.setattr(evaluator, "evaluate_sample",
                        lambda *args: ([trade], {"census": {}, "fold_boundaries": None}))
    monkeypatch.setattr(mechanics, "day_cluster_ci", lambda _: [0.01, 0.02])
    monkeypatch.setattr(evaluator, "_mechanics", lambda: mechanics)

    report = evaluator.build_report(Path(), Path(), Path())

    assert report["primary"]["overall_funding_inclusive"]["n"] == 1
    assert report["gate"]["verdict"] == "REJECT"
