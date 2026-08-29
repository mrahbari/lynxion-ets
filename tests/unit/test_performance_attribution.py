import csv
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "performance_attribution.py"


def _module():
    spec = importlib.util.spec_from_file_location("performance_attribution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_attribution_deduplicates_adjusts_for_fees_and_computes_drawdown(tmp_path):
    path = tmp_path / "trades.csv"
    rows = [
        {"trade_id": "a", "symbol": "BTCUSDT", "strategy": "alpha", "side": "BUY", "entry_timestamp": "2026-08-13T13:00:00+00:00", "exit_timestamp": "2026-08-13T13:10:00+00:00", "entry_price": "100", "quantity": "1", "pnl_usdt": "1", "fees_usdt": "-0.1", "exit_reason": "MARKET", "confidence": "0.55", "regime": "trend", "timeframe": "1m", "duration_seconds": "600", "initial_stop_loss": "99", "initial_take_profit": "102", "is_execution_unwind": "False"},
        {"trade_id": "a", "symbol": "BTCUSDT", "strategy": "alpha", "side": "BUY", "entry_timestamp": "2026-08-13T13:00:00+00:00", "exit_timestamp": "2026-08-13T13:20:00+00:00", "entry_price": "100", "quantity": "1", "pnl_usdt": "2", "fees_usdt": "-0.2", "exit_reason": "TAKE_PROFIT_MARKET", "confidence": "0.55", "regime": "trend", "timeframe": "1m", "duration_seconds": "1200", "initial_stop_loss": "99", "initial_take_profit": "102", "is_execution_unwind": "False"},
        {"trade_id": "b", "symbol": "ETHUSDT", "strategy": "beta", "side": "SELL", "entry_timestamp": "2026-08-13T13:30:00+00:00", "exit_timestamp": "2026-08-13T14:00:00+00:00", "entry_price": "50", "quantity": "0.4", "pnl_usdt": "-1", "fees_usdt": "-0.1", "exit_reason": "STOP_MARKET", "confidence": "0.75", "regime": "range", "timeframe": "1m", "duration_seconds": "1800", "initial_stop_loss": "51", "initial_take_profit": "48", "is_execution_unwind": "True"},
    ]
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    before = path.read_bytes()

    report = _module().build_report(str(path), "2026-08-13T13:15:00+00:00")

    assert report["data_quality"]["duplicate_rows"] == 1
    assert report["cohort_timestamp_field"] == "entry_timestamp"
    assert report["overall"]["n"] == 1
    assert report["overall"]["recorded_pnl_usdt"] == -1.0
    assert report["overall"]["fees_usdt"] == -0.1
    assert report["overall"]["cost_adjusted_pnl_usdt"] == -1.1
    assert report["overall"]["expectancy_usdt"] == -1.1
    assert report["overall"]["profit_factor"] == 0.0
    assert report["overall"]["max_drawdown_usdt"] == 1.1
    assert report["by_side"]["SELL"]["execution_unwinds"] == 1
    assert report["by_confidence_bucket"]["0.70-0.80"]["n"] == 1
    assert path.read_bytes() == before
