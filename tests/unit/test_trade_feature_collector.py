"""Unit tests for TradeFeatureCollector (E12 / Research)."""

import csv
import json
import os
import tempfile
import pytest

from infrastructure.execution.trade_feature_collector import TradeFeatureCollector, CSV_HEADER


@pytest.fixture
def temp_collector(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_p = os.path.join(tmpdir, "trade_features.csv")
        journal_p = os.path.join(tmpdir, "live_order_journal.json")
        ledger_p = os.path.join(tmpdir, "execution_truth_ledger.jsonl")
        forensic_p = os.path.join(tmpdir, "forensic.log")

        collector = TradeFeatureCollector(
            csv_path=csv_p,
            journal_path=journal_p,
            ledger_path=ledger_p,
            forensic_path=forensic_p,
            poll_interval_seconds=1.0,
        )

        mock_rows = [
            {
                "trade_id": "pos_1001",
                "symbol": "XMRUSDT",
                "strategy": "trend_following",
                "side": "BUY",
                "entry_timestamp": "2026-08-09T10:00:00Z",
                "exit_timestamp": "2026-08-09T10:05:00Z",
                "entry_price": "155.50",
                "exit_price": "160.00",
                "quantity": "1.5",
                "pnl_usdt": "6.75",
                "fees_usdt": "-0.05",
                "exit_reason": "TAKE_PROFIT_MARKET",
                "actual_fill_price": "155.50",
                "initial_stop_loss": "",
                "initial_take_profit": "",
                "risk_usdt": "",
                "r_multiple": "",
                "confidence": "0.8",
                "regime": "TRENDING",
                "timeframe": "1m",
                "signal_direction": "BUY",
                "duration_seconds": "300.0",
                "sl_distance_pct": "",
                "tp_distance_pct": "",
                "order_id": "order_1001",
                "order_ref": "ref_1001",
                "client_order_id": "client_1001",
                "exchange": "bingx",
                "execution_latency_ms": "45.2",
                "is_execution_unwind": "False",
                "status": "FILLED",
            }
        ]

        monkeypatch.setattr(collector, "reconstruct_exchange_completed_trades", lambda: mock_rows)

        yield collector, csv_p, journal_p, ledger_p, mock_rows


@pytest.mark.unit
def test_csv_initialization_and_header(temp_collector):
    collector, csv_p, _, _, _ = temp_collector
    assert os.path.exists(csv_p)
    with open(csv_p, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == CSV_HEADER


@pytest.mark.unit
def test_backfill_historical_trades_and_idempotency(temp_collector):
    collector, csv_p, _, _, _ = temp_collector

    # First backfill run
    count1 = collector.backfill_historical_trades(purge_incomplete=False)
    assert count1 == 1

    # Check row contents
    with open(csv_p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["trade_id"] == "pos_1001"
        assert rows[0]["symbol"] == "XMRUSDT"
        assert rows[0]["quantity"] == "1.5"
        assert rows[0]["entry_price"] == "155.50"
        assert rows[0]["pnl_usdt"] == "6.75"

    # Second backfill run (must be idempotent: 0 new rows)
    count2 = collector.backfill_historical_trades(purge_incomplete=False)
    assert count2 == 0

    with open(csv_p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1


@pytest.mark.unit
def test_emergency_unwind_classification(temp_collector, monkeypatch):
    collector, csv_p, _, _, _ = temp_collector

    unwind_mock = [
        {
            "trade_id": "unwind_2002",
            "symbol": "BTCUSDT",
            "strategy": "trend_following",
            "side": "SELL",
            "entry_timestamp": "2026-08-09T10:05:00Z",
            "exit_timestamp": "2026-08-09T10:05:05Z",
            "entry_price": "63300.0",
            "exit_price": "63350.0",
            "quantity": "0.1",
            "pnl_usdt": "-5.0",
            "fees_usdt": "-0.1",
            "exit_reason": "EMERGENCY_UNWIND",
            "actual_fill_price": "63300.0",
            "initial_stop_loss": "",
            "initial_take_profit": "",
            "risk_usdt": "",
            "r_multiple": "",
            "confidence": "",
            "regime": "",
            "timeframe": "1m",
            "signal_direction": "SELL",
            "duration_seconds": "5.0",
            "sl_distance_pct": "",
            "tp_distance_pct": "",
            "order_id": "order_unwind_2002",
            "order_ref": "ref_unwind_2002",
            "client_order_id": "client_unwind_2002",
            "exchange": "bingx",
            "execution_latency_ms": "120.5",
            "is_execution_unwind": "True",
            "status": "EMERGENCY_UNWIND",
        }
    ]

    monkeypatch.setattr(collector, "reconstruct_exchange_completed_trades", lambda: unwind_mock)
    collector.backfill_historical_trades(purge_incomplete=True)

    with open(csv_p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        unwind_row = rows[0]
        assert unwind_row["trade_id"] == "unwind_2002"
        assert unwind_row["exit_reason"] == "EMERGENCY_UNWIND"
        assert unwind_row["is_execution_unwind"] == "True"


@pytest.mark.unit
def test_metadata_forwarding_end_to_end():
    """Verify that metadata fields passed to record_intent arrive unchanged in intent_metadata_map."""
    from infrastructure.execution.live_order_journal import LiveOrderJournal
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_p = os.path.join(tmpdir, "live_order_journal.json")
        journal = LiveOrderJournal(path=journal_p)

        ref = journal.record_intent(
            symbol="BTC-USDT",
            side="BUY",
            quantity="0.01",
            exchange="bingx",
            client_order_id="client_test_999",
            stop_loss="62000.0",
            take_profit="65000.0",
            confidence="0.85",
            regime="TRENDING_UP",
            strategy="trend_following",
        )

        assert ref is not None
        collector = TradeFeatureCollector(journal_path=journal_p)
        meta_map = collector._load_intent_metadata_map()

        meta = meta_map.get("client_test_999") or meta_map.get(ref)
        assert meta is not None
        assert meta["initial_stop_loss"] == "62000.0"
        assert meta["initial_take_profit"] == "65000.0"
        assert meta["confidence"] == "0.85"
        assert meta["regime"] == "TRENDING_UP"
        assert meta["strategy"] == "trend_following"


@pytest.mark.unit
def test_metadata_is_retained_when_submitted_record_adds_exchange_order_id():
    """Exchange-history matching by order ID must retain the original intent metadata."""
    from infrastructure.execution.live_order_journal import LiveOrderJournal

    with tempfile.TemporaryDirectory() as tmpdir:
        journal_p = os.path.join(tmpdir, "live_order_journal.json")
        journal = LiveOrderJournal(path=journal_p)
        ref = journal.record_intent(
            symbol="BTC-USDT",
            side="BUY",
            quantity="0.01",
            exchange="bingx",
            client_order_id="exchange-client-id",
            stop_loss="62000.0",
            take_profit="65000.0",
            confidence="0.85",
            regime="TRENDING_UP",
            strategy="trend_following",
        )
        journal.record_submitted(ref, "exchange-order-id", "bingx")

        meta = TradeFeatureCollector(journal_path=journal_p)._load_intent_metadata_map()[
            "exchange-order-id"
        ]
        assert meta == {
            "initial_stop_loss": "62000.0",
            "initial_take_profit": "65000.0",
            "confidence": "0.85",
            "regime": "TRENDING_UP",
            "strategy": "trend_following",
        }


@pytest.mark.unit
def test_order_journal_metadata_uses_canonical_execution_order_fields():
    """Journal attribution must use Order SL/TP prices and its parent intent context."""
    from datetime import datetime
    from decimal import Decimal
    from domain.entities import ExecutionIntent, Order
    from domain.enums.order_side import OrderSide
    from domain.value_objects import Money, Percentage, Symbol
    from infrastructure.brokers.multi_broker_service import extract_order_journal_metadata

    parent_intent = ExecutionIntent(
        symbol=Symbol("BTCUSDT"),
        strategy_name="trend_following",
        side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal("0.85")),
        risk_parameters={"stop_loss": 62000.0, "take_profit": 65000.0},
        timestamp=datetime.now(),
        metadata={"regime_context": "TRENDING_UP"},
    )
    order = Order(
        symbol=Symbol("BTCUSDT"),
        side=OrderSide.BUY,
        quantity=Decimal("0.01"),
        parent_execution_intent=parent_intent,
        stop_loss_price=Money(Decimal("62000"), "USDT"),
        take_profit_price=Money(Decimal("65000"), "USDT"),
    )

    assert extract_order_journal_metadata(order) == {
        "stop_loss": Decimal("62000"),
        "take_profit": Decimal("65000"),
        "confidence": Decimal("0.85"),
        "regime": "TRENDING_UP",
        "strategy": "trend_following",
    }



@pytest.mark.unit
def test_background_thread_start_and_stop(temp_collector):
    collector, _, _, _, _ = temp_collector
    collector.start()
    assert collector._thread is not None
    assert collector._thread.is_alive()

    collector.stop()
    assert not collector._thread.is_alive()
