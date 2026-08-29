import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "audit_live_order_journal.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("audit_live_order_journal", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_report_uses_latest_state_per_order_ref_without_writing(tmp_path):
    journal_path = tmp_path / "orders.jsonl"
    records = [
        {"order_ref": "a", "status": "INTENT", "symbol": "BTCUSDT", "side": "BUY", "quantity": "2"},
        {"order_ref": "a", "status": "SUBMITTED", "order_id": "broker-a", "exchange": "bingx"},
        {"order_ref": "a", "status": "FILLED", "filled_qty": "2", "total_qty": "2"},
        {"order_ref": "b", "status": "INTENT", "symbol": "ETHUSDT", "side": "SELL", "quantity": "3"},
    ]
    journal_path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    before = journal_path.read_bytes()

    report = _load_script_module().build_report(str(journal_path))

    assert report["unique_orders"] == 2
    assert report["status_counts"] == {"FILLED": 1, "INTENT": 1}
    assert report["in_flight_count"] == 1
    assert report["in_flight_without_order_id"] == 1
    assert report["order_exchange_map_count"] == 1
    assert report["net_positions"] == {"BTCUSDT": "2"}
    assert journal_path.read_bytes() == before
