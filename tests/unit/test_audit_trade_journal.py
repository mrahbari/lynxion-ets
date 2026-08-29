import csv
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "audit_trade_journal.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("audit_trade_journal", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_report_deduplicates_by_final_trade_id_and_honors_cohort_boundary(tmp_path):
    journal_path = tmp_path / "trades.csv"
    rows = [
        {"trade_id": "a", "exit_timestamp": "2026-08-13T13:00:00+00:00", "pnl_usdt": "1", "fees_usdt": "0.1", "side": "BUY", "exit_reason": "MARKET", "initial_stop_loss": "1", "initial_take_profit": "2"},
        {"trade_id": "a", "exit_timestamp": "2026-08-13T14:00:00+00:00", "pnl_usdt": "2", "fees_usdt": "0.2", "side": "BUY", "exit_reason": "TAKE_PROFIT_MARKET", "initial_stop_loss": "1", "initial_take_profit": "2"},
        {"trade_id": "b", "exit_timestamp": "2026-08-13T14:30:00+00:00", "pnl_usdt": "-1", "fees_usdt": "0.1", "side": "SELL", "exit_reason": "STOP_MARKET", "initial_stop_loss": "0", "initial_take_profit": "0"},
    ]
    with journal_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    before = journal_path.read_bytes()

    report = _load_script_module().build_report(str(journal_path), "2026-08-13T13:30:00+00:00")

    assert report["source_rows"] == 3
    assert report["unique_trade_ids"] == 2
    assert report["duplicate_rows"] == 1
    assert report["cohort_trade_ids"] == 2
    assert report["net_pnl_usdt"] == 1.0
    assert report["profit_factor"] == 2.0
    assert report["missing_initial_stop_loss"] == 1
    assert journal_path.read_bytes() == before
