"""R2 — operational hardening: startup preflight, local net-position book, restart stress."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from shared.preflight import run_preflight
from infrastructure.execution.live_order_journal import LiveOrderJournal


def _settings(paper, testnet, placement, key="REALKEY123", secret="REALSECRET123", broker="bingx"):
    b = SimpleNamespace(default_broker=broker, paper_trading=paper, testnet=testnet)
    setattr(b, f"{broker}_testnet", testnet)
    setattr(b, f"{broker}_order_placement_enabled", placement)
    setattr(b, f"{broker}_api_key", key)
    setattr(b, f"{broker}_secret_key", secret)
    return SimpleNamespace(broker=b)


# ---- preflight ----------------------------------------------------------------

def test_preflight_paper_ok():
    pf = run_preflight(_settings(paper=True, testnet=True, placement=True), env={})
    assert pf["mode"] == "PAPER" and pf["ok"] is True


def test_preflight_testnet_ok_with_keys():
    pf = run_preflight(_settings(paper=False, testnet=True, placement=True), env={})
    assert pf["mode"] == "TESTNET" and pf["ok"] is True


def test_preflight_testnet_blocks_on_placeholder_keys():
    pf = run_preflight(_settings(paper=False, testnet=True, placement=True, key="your_key_here"), env={})
    assert pf["mode"] == "TESTNET" and pf["ok"] is False and pf["blocking"]


def test_preflight_live_ok_with_optin_and_keys():
    pf = run_preflight(_settings(paper=False, testnet=False, placement=True), env={"LIVE_TRADING": "true"})
    assert pf["mode"] == "LIVE" and pf["ok"] is True
    assert any("LIVE" in w for w in pf["warnings"])


def test_preflight_live_endpoint_without_optin_is_blocked_mode():
    pf = run_preflight(_settings(paper=False, testnet=False, placement=True), env={})
    assert pf["mode"] == "BLOCKED"
    assert any("BLOCKED" in w for w in pf["warnings"])


# ---- local net-position book --------------------------------------------------

def test_net_position_book_from_fills(tmp_path):
    j = LiveOrderJournal(path=str(tmp_path / "j.jsonl"))
    r1 = j.record_intent("BTCUSDT", "BUY", "1.0", "bingx", "x1"); j.record_submitted(r1, "O1", "bingx")
    j.record_fill(r1, "1.0", "1.0")
    r2 = j.record_intent("BTCUSDT", "SELL", "0.4", "bingx", "x2"); j.record_submitted(r2, "O2", "bingx")
    j.record_fill(r2, "0.4", "0.4")
    r3 = j.record_intent("ETHUSDT", "BUY", "2.0", "bingx", "x3"); j.record_submitted(r3, "O3", "bingx")
    j.record_fill(r3, "2.0", "2.0")
    book = j.net_positions()
    assert book["BTCUSDT"] == Decimal("0.6")    # 1.0 long - 0.4 sell
    assert book["ETHUSDT"] == Decimal("2.0")


# ---- restart / recovery stress -----------------------------------------------

def test_restart_recovery_stress(tmp_path):
    p = str(tmp_path / "j.jsonl")
    j = LiveOrderJournal(path=p)
    refs = []
    for i in range(50):
        r = j.record_intent(f"SYM{i % 5}USDT", "BUY" if i % 2 == 0 else "SELL", "1.0", "bingx", f"x{i}")
        j.record_submitted(r, f"OID{i}", "bingx")
        if i % 3 == 0:
            j.record_fill(r, "1.0", "1.0")            # some filled
        refs.append(r)
    # Many restart cycles must reproduce identical state.
    snap = LiveOrderJournal(path=p).recover()
    for _ in range(5):
        snap2 = LiveOrderJournal(path=p).recover()
        assert snap2["total_orders"] == snap["total_orders"] == 50
        assert snap2["status_counts"] == snap["status_counts"]
        assert len(snap2["order_exchange_map"]) == len(snap["order_exchange_map"]) == 50
