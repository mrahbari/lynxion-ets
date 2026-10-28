"""B3 — durable live recovery: order journal lifecycle + crash/restart recovery."""

import pytest

from infrastructure.execution.live_order_journal import LiveOrderJournal


def test_protective_ack_write_failure_keeps_entry_intent_unknown(tmp_path):
    path = tmp_path / "entry.jsonl"
    journal = LiveOrderJournal(path=str(path))
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx")
    collision = tmp_path / "cannot_write"
    collision.mkdir()
    journal._path = str(collision)
    with pytest.raises(OSError):
        journal.record_submitted(ref, "MAIN-1", "bingx", protective_order_ids={"STOP_MARKET": "SL-1"})
    assert journal.in_flight()[0]["status"] == "INTENT"
    assert LiveOrderJournal(path=str(path)).in_flight()[0]["status"] == "INTENT"

@pytest.mark.parametrize("ids", [{"STOP_MARKET": None}, {"STOP": "SL-1"}, {"STOP_MARKET": True}])
def test_invalid_protective_identity_never_promotes_entry(tmp_path, ids):
    journal = LiveOrderJournal(path=str(tmp_path / "entry.jsonl"))
    ref = journal.record_intent("BTC-USDT", "BUY", "1", "bingx")
    with pytest.raises(ValueError):
        journal.record_submitted(ref, "MAIN-1", "bingx", protective_order_ids=ids)
    assert journal.in_flight()[0]["status"] == "INTENT"

def test_unknown_protection_survives_reopen_without_fabricating_fill(tmp_path):
    path = tmp_path / "protection.jsonl"
    journal = LiveOrderJournal(path=str(path))
    entry = journal.record_intent("BTC-USDT", "BUY", "1", "bingx")
    journal.record_submitted(entry, "ENTRY-1", "bingx")
    before = path.read_bytes()
    ref = journal.record_protection_unknown("BTC-USDT", "SELL", "1", "bingx", entry_order_ref=entry)
    assert path.read_bytes().startswith(before)
    restored = LiveOrderJournal(path=str(path))
    record = next(row for row in restored.in_flight() if row["order_ref"] == ref)
    assert record["status"] == "PROTECTION_UNKNOWN" and record["entry_order_ref"] == entry
    assert record["order_id"] is None and record["purpose"] == "PROTECTION"
    assert restored.net_positions() == {}
    assert restored.order_exchange_map() == {"ENTRY-1": ("bingx", "BTC-USDT")}
    with pytest.raises(RuntimeError):
        restored.record_intent("ETH-USDT", "BUY", "1", "bingx")

def test_unknown_protection_rejects_wrong_parent_symbol(tmp_path):
    journal = LiveOrderJournal(path=str(tmp_path / "p.jsonl"))
    entry = journal.record_intent("BTC-USDT", "BUY", "1", "bingx")
    journal.record_submitted(entry, "ENTRY-1", "bingx")
    with pytest.raises(ValueError):
        journal.record_protection_unknown("ETH-USDT", "SELL", "1", "bingx", entry_order_ref=entry)

def test_unknown_protection_write_failure_is_not_silently_accepted(tmp_path):
    blocked = tmp_path / "not_a_directory"
    blocked.write_text("synthetic")
    journal = LiveOrderJournal(path=str(blocked / "p.jsonl"))
    with pytest.raises(OSError):
        journal.record_protection_unknown("BTC-USDT", "SELL", "1", "bingx")
    assert journal.in_flight() == []

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


def test_intent_fsync_failure_is_not_reported_as_durable(monkeypatch, tmp_path):
    import os

    journal = LiveOrderJournal(path=str(tmp_path / "journal.jsonl"))
    monkeypatch.setattr(os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("fsync failed")))

    with pytest.raises(OSError, match="fsync failed"):
        journal.record_intent("BTCUSDT", "BUY", "1", "bingx", "stable-client-id")
    assert journal.in_flight() == []


def test_failed_terminal_write_keeps_intent_recoverable_in_memory(tmp_path):
    path = tmp_path / "orders.jsonl"
    journal = LiveOrderJournal(path=str(path))
    ref = journal.record_intent("BTC-USDT", "BUY", "0.001", "bingx", "stable-client-id")
    blocked_path = tmp_path / "path-is-a-directory"
    blocked_path.mkdir()
    journal._path = str(blocked_path)

    journal.record_failed(ref, "broker response unknown")

    assert [order["order_ref"] for order in journal.in_flight()] == [ref]
    assert LiveOrderJournal(path=str(path)).in_flight()[0]["order_ref"] == ref


def test_unresolved_intent_blocks_new_identity_across_symbols_and_restart(tmp_path):
    path = tmp_path / "orders.jsonl"
    journal = LiveOrderJournal(path=str(path))
    first = journal.record_intent("FET-USDT", "BUY", "10", "bingx", "first-client-id")
    before = path.read_bytes()

    with pytest.raises(RuntimeError, match="unresolved INTENT"):
        journal.record_intent("BTC-USDT", "SELL", "1", "bingx", "second-client-id")
    assert path.read_bytes() == before
    assert len(journal.in_flight()) == 1

    restarted = LiveOrderJournal(path=str(path))
    with pytest.raises(RuntimeError, match="unresolved INTENT"):
        restarted.record_intent("ETH-USDT", "BUY", "1", "bingx", "third-client-id")
    assert path.read_bytes() == before

    restarted.record_submitted(first, "acknowledged-id", "bingx")
    second = restarted.record_intent("BTC-USDT", "SELL", "1", "bingx", "second-client-id")
    assert second != first


def test_concurrent_intents_admit_only_one_until_first_resolves(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    journal = LiveOrderJournal(path=str(tmp_path / "orders.jsonl"))
    barrier = Barrier(2)

    def attempt(index):
        barrier.wait()
        try:
            return journal.record_intent(f"SYM{index}-USDT", "BUY", "1", "bingx", f"client-{index}")
        except RuntimeError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (1, 2)))
    assert sum(result is not None for result in results) == 1
    assert len(journal.in_flight()) == 1
