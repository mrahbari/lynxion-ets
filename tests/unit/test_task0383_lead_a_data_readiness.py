import csv
import json

from scripts.audit_lead_a_data_readiness import audit


def fixture_root(tmp_path, *, include_exit=False):
    journal = tmp_path / "data/research/investor_release/trade_journal_baseline_v1.csv"
    journal.parent.mkdir(parents=True)
    with journal.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["trade_id", "symbol"])
        writer.writeheader()
        writer.writerow({"trade_id": "1", "symbol": "BTCUSDT"})

    recent = tmp_path / "data/research/task0180/recent_bingx_exits_98.json"
    recent.parent.mkdir(parents=True)
    recent.write_text(json.dumps({"trades": [{"symbol": "BTCUSDT"}]}), encoding="utf-8")

    candle = tmp_path / "data/history/raw/1m/BTC-USDT.csv"
    candle.parent.mkdir(parents=True)
    candle.write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")

    events = tmp_path / "data/observability/forward_exit/events/one.jsonl"
    events.parent.mkdir(parents=True)
    rows = [{
        "event_type": "POSITION_OBSERVED",
        "position_key": "BTCUSDT:LONG:1",
        "price_source": "MARK",
    }]
    if include_exit:
        rows.append({"event_type": "EXIT_FILLED", "position_key": "BTCUSDT:LONG:1"})
    events.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return tmp_path


def test_current_contract_fails_when_market_identity_and_join_are_unknown(tmp_path):
    result = audit(fixture_root(tmp_path, include_exit=True))

    assert result["verdict"] == "INSUFFICIENT_PROVENANCE"
    assert not result["readiness_gates"]["closed_trade_candle_market_identity_declared"]
    assert not result["readiness_gates"]["single_dataset_joins_path_to_realized_exit"]


def test_forward_exit_fill_absence_is_reported(tmp_path):
    result = audit(fixture_root(tmp_path))

    assert result["forward_exit_ledger"]["mark_price_observations"] == 1
    assert result["forward_exit_ledger"]["exit_fill_events"] == 0
    assert not result["readiness_gates"]["forward_exit_fill_events_present"]
