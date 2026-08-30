import importlib.util
from pathlib import Path


def module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_cross_symbol_funding_c12.py"
    spec = importlib.util.spec_from_file_location("edge_c12", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_unopened_symbol_universe_is_frozen():
    assert module().SYMBOLS == ("BNBUSDT", "XRPUSDT", "ADAUSDT")


def test_c12_reuses_c10_execution_mechanics():
    evaluator = module()
    mechanics = evaluator._load_c10()
    assert mechanics.FOLDS == evaluator.FOLDS == 4
    assert mechanics.PRIMARY_COST == evaluator.PRIMARY_COST == 0.003


def test_zero_threshold_severity_is_preserved_as_undefined():
    evaluator = module()
    mechanics = evaluator._load_c10()
    assert mechanics.symbol_trades
    assert "undefined-zero-threshold" in Path(evaluator.__file__).read_text(encoding="utf-8")


def test_report_identity_can_be_set_without_changing_mechanics(monkeypatch, tmp_path):
    evaluator = module()
    mechanics = evaluator._load_c10()
    monkeypatch.setattr(mechanics, "causal_funding", lambda path: None)
    monkeypatch.setattr(mechanics, "load_price", lambda path: None)
    monkeypatch.setattr(mechanics, "symbol_trades", lambda symbol, funding, price: ([], {}))
    monkeypatch.setattr(evaluator, "_load_c10", lambda: mechanics)
    report = evaluator.build_report(tmp_path, tmp_path, "C-13", "edge-candidate-register-v12")
    assert (report["candidate"], report["protocol"]) == (
        "C-13", "edge-candidate-register-v12"
    )
