import importlib.util
from pathlib import Path


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_independent_long_trend_c15.py"
    spec = importlib.util.spec_from_file_location("edge_c15", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_new_universe_is_frozen_and_disjoint_from_c14():
    evaluator = module()
    mechanics = evaluator._mechanics()
    assert evaluator.SYMBOLS == ("DOGEUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT", "AVAXUSDT")
    assert set(evaluator.SYMBOLS).isdisjoint(mechanics.SYMBOLS)
