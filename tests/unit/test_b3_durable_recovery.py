"""B3 — durable live recovery: order journal lifecycle + crash/restart recovery."""

import pytest

from infrastructure.execution.live_order_journal import LiveOrderJournal


def test_ack_field_belongs_to_order_not_execution_intent():
    import inspect
    from domain.entities.order import Order, ExecutionIntent
    from domain.entities import OrderSide
    from domain.value_objects import Symbol
    from decimal import Decimal
    assert "protective_order_ids" in inspect.signature(Order).parameters
    assert "protective_order_ids" not in inspect.signature(ExecutionIntent).parameters
    names = list(inspect.signature(ExecutionIntent).parameters)
    assert names == ["symbol", "strategy_name", "side", "intent_confidence", "risk_parameters",
                     "timestamp", "fused_signal", "metadata", "requested_leverage", "intent_id"]
    order = Order(Symbol("BTC-USDT"), OrderSide.BUY, Decimal("1"), protective_order_ids={"STOP_MARKET": "SL-1"})
    assert order.protective_order_ids == {"STOP_MARKET": "SL-1"}


def test_initial_protective_metadata_survives_reopen(tmp_path):
    path = str(tmp_path / "entry.jsonl")
    journal = LiveOrderJournal(path)
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx")
    ids = {"STOP_MARKET": "SL-1", "TAKE_PROFIT_MARKET": "TP-1"}
    journal.record_submitted(ref, "ENTRY-1", "bingx", protective_order_ids=ids)
    ids["STOP_MARKET"] = "MUTATED"
    record = LiveOrderJournal(path).in_flight()[0]
    assert record["protective_order_ids"]["STOP_MARKET"] == "SL-1"
    assert "filled_qty" not in record


def test_initial_protective_write_failure_preserves_intent(tmp_path):
    journal = LiveOrderJournal(str(tmp_path / "entry.jsonl"))
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx")
    journal._path = str(tmp_path)
    with pytest.raises(OSError):
        journal.record_submitted(ref, "ENTRY-1", "bingx", protective_order_ids={"STOP_MARKET": "SL-1"})
    assert journal.in_flight()[0]["status"] == "INTENT"


@pytest.mark.parametrize("ids", [{"STOP_MARKET": None}, {"STOP_MARKET": True}, {"STOP": "SL-1"}])
def test_initial_invalid_protective_metadata_preserves_intent(tmp_path, ids):
    journal = LiveOrderJournal(str(tmp_path / "entry.jsonl"))
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx")
    with pytest.raises(ValueError):
        journal.record_submitted(ref, "ENTRY-1", "bingx", protective_order_ids=ids)
    assert journal.in_flight()[0]["status"] == "INTENT"


def test_journal_lifecycle_intent_submitted_terminal(tmp_path):
    j = LiveOrderJournal(path=str(tmp_path / "j.jsonl"))
    ref = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx", client_order_id="x123")
    assert len(j.in_flight()) == 1                      # INTENT is in-flight
    j.record_submitted(ref, "OID1", "bingx")
    assert len(j.in_flight()) == 1                      # SUBMITTED still in-flight (not terminal)
    assert j.order_exchange_map()["OID1"] == ("bingx", "BTC-USDT")
    j.record_terminal(ref, "FILLED", fill_price="60000")
    assert j.in_flight() == []                          # terminal -> no longer in-flight


def test_crash_after_send_recovers_in_flight(tmp_path):
    p = str(tmp_path / "j.jsonl")
    j1 = LiveOrderJournal(path=p)
    ref = j1.record_intent("ETH-USDT", "BUY", "0.01", "bingx", client_order_id="xabc")
    j1.record_submitted(ref, "OID9", "bingx")           # broker accepted...
    # ...process crashes here before any terminal record.

    j2 = LiveOrderJournal(path=p)                         # restart -> recover from journal
    rec = j2.recover()
    assert rec["total_orders"] == 1
    assert len(rec["in_flight"]) == 1                    # flagged for broker reconciliation (B4)
    assert rec["order_exchange_map"]["OID9"] == ("bingx", "ETH-USDT")
    assert rec["status_counts"].get("SUBMITTED") == 1


def test_intent_without_send_is_recoverable(tmp_path):
    """Lost-write window: a crash AFTER the intent record but BEFORE the broker ack still
    leaves a recoverable trace (never a live order with no local record)."""
    p = str(tmp_path / "j.jsonl")
    j1 = LiveOrderJournal(path=p)
    j1.record_intent("SOL-USDT", "BUY", "1", "bingx", client_order_id="xsol")
    j2 = LiveOrderJournal(path=p)
    inflight = j2.in_flight()
    assert len(inflight) == 1 and inflight[0]["status"] == "INTENT"


def test_failed_intent_not_in_flight(tmp_path):
    p = str(tmp_path / "j.jsonl")
    j = LiveOrderJournal(path=p)
    ref = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx")
    j.record_failed(ref, "rejected")
    assert j.in_flight() == []                           # failed -> not in-flight


def test_exact_exchange_order_id_resolves_lifecycle_reference(tmp_path):
    j = LiveOrderJournal(path=str(tmp_path / "j.jsonl"))
    ref = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx")
    j.record_submitted(ref, "OID-EXACT", "bingx")

    assert j.order_ref_for_exchange_order("OID-EXACT") == ref
    assert j.order_ref_for_exchange_order("UNKNOWN") is None


def test_ambiguous_exchange_order_id_fails_closed(tmp_path):
    j = LiveOrderJournal(path=str(tmp_path / "j.jsonl"))
    first = j.record_intent("BTC-USDT", "BUY", "0.001", "bingx")
    j.record_submitted(first, "OID-DUPLICATE", "bingx")
    second = j.record_intent("ETH-USDT", "BUY", "0.01", "bingx")
    j.record_submitted(second, "OID-DUPLICATE", "bingx")

    assert j.order_ref_for_exchange_order("OID-DUPLICATE") is None
