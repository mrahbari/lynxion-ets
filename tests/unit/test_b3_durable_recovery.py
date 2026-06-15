"""B3 — durable live recovery: order journal lifecycle + crash/restart recovery."""

import pytest

from infrastructure.execution.live_order_journal import LiveOrderJournal


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
