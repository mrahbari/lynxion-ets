import importlib.util
from pathlib import Path


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_oi_flush_reversal_c17.py"
    spec = importlib.util.spec_from_file_location("edge_c17", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_c17_universe_is_disjoint_from_c16():
    evaluator = module(); mechanics = evaluator._mechanics()
    assert set(evaluator.SYMBOLS).isdisjoint(mechanics.SYMBOLS)


def test_contraction_feature_is_negative_oi_return(monkeypatch):
    evaluator = module(); mechanics = evaluator._mechanics()
    import pandas as pd
    base = pd.DataFrame({"price_return": [0.1] * 200, "oi_return": [-0.2] * 200}, index=range(200))
    monkeypatch.setattr(mechanics, "causal_features", lambda *args: base)
    monkeypatch.setattr(evaluator, "_mechanics", lambda: mechanics)
    features = evaluator.causal_features(None, None)
    assert (features["oi_contraction"] == 0.2).all()
