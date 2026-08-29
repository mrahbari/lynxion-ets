import importlib.util
from types import SimpleNamespace
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "audit_vst_protection.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("audit_vst_protection", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_protection_coverage_matches_normalized_symbols_and_reports_gaps():
    positions = [SimpleNamespace(symbol=SimpleNamespace(value="BTCUSDT")), SimpleNamespace(symbol="ETH-USDT")]
    pending = [
        {"symbol": "BTC-USDT", "type": "STOP_MARKET"},
        {"symbol": "BTC-USDT", "type": "TAKE_PROFIT_MARKET"},
        {"symbol": "ETHUSDT", "type": "STOP_MARKET"},
    ]

    report = _load_script_module().protection_coverage(positions, pending)

    assert report["open_position_count"] == 2
    assert report["pending_order_types"] == {"STOP_MARKET": 2, "TAKE_PROFIT_MARKET": 1}
    assert report["positions_missing_stop_loss"] == []
    assert report["positions_missing_take_profit"] == ["ETHUSDT"]
