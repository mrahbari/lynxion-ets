"""Tests for the Execution Truth Ledger (ETL) and the race-free authorize_and_send path.

Covers: append-only hash chaining, tamper detection, that a decision record is written
BEFORE any send (and for blocked orders too — cannot be bypassed), and that under
concurrent flag flipping + kill-switch/breaker chaos no order is ever sent while killed
or breaker-open, and no LIVE send is recorded outside the allowed flag state.
"""

import os
import random
import tempfile
import threading
from types import SimpleNamespace

import pytest

from shared.execution_truth_ledger import ExecutionTruthLedger
from shared.live_execution_guard import LiveExecutionGuard, ExecutionMode


@pytest.fixture
def ledger(tmp_path):
    return ExecutionTruthLedger(path=str(tmp_path / "etl.jsonl"))


@pytest.fixture(autouse=True)
def _reset_global_breakers():
    # The circuit breaker is process-global (by design); clear it between tests so an
    # OPEN breaker from one test does not bleed into the next.
    from shared.circuit_breaker import circuit_breaker_manager
    from shared.live_execution_guard import live_execution_guard
    circuit_breaker_manager.circuit_breakers.clear()
    live_execution_guard.disengage_kill_switch()
    old_enforcer = live_execution_guard._risk_enforcer
    live_execution_guard._risk_enforcer = lambda o: (True, "")
    yield
    circuit_breaker_manager.circuit_breakers.clear()
    live_execution_guard.disengage_kill_switch()
    live_execution_guard._risk_enforcer = old_enforcer


@pytest.fixture
def guard():
    g = LiveExecutionGuard()
    g._risk_enforcer = lambda o: (True, "")
    return g


def _settings(paper, placement, testnet, broker="bingx"):
    b = SimpleNamespace(paper_trading=paper, testnet=testnet)
    setattr(b, f"{broker}_order_placement_enabled", placement)
    setattr(b, f"{broker}_testnet", testnet)
    return SimpleNamespace(broker=b)


def _order():
    return SimpleNamespace(symbol=SimpleNamespace(value="TEST/USDT"), side=SimpleNamespace(name="BUY"))


# ---- ledger primitives -------------------------------------------------------------

def test_append_is_hash_chained_and_immutable(ledger):
    r1 = ledger.append("decision", {"order_ref": "a", "route": "LIVE"})
    r2 = ledger.append("result", {"order_ref": "a", "success": True})
    assert r2["prev_hash"] == r1["hash"] and r2["seq"] == r1["seq"] + 1
    assert ledger.verify() == {"ok": True, "records": 2, "broken_at": None}


def test_tamper_is_detected(ledger):
    ledger.append("decision", {"order_ref": "a", "symbol": "BTC/USDT", "route": "LIVE"})
    ledger.append("result", {"order_ref": "a", "success": True})
    lines = open(ledger.path).read().splitlines()
    lines[0] = lines[0].replace("BTC/USDT", "ETH/USDT")          # edit a committed record
    open(ledger.path, "w").write("\n".join(lines) + "\n")
    v = ledger.verify()
    assert v["ok"] is False and v["broken_at"] == 1


def test_resumes_seq_and_chain_across_instances(tmp_path):
    p = str(tmp_path / "etl.jsonl")
    a = ExecutionTruthLedger(path=p)
    last = a.append("decision", {"order_ref": "x"})
    b = ExecutionTruthLedger(path=p)                              # fresh instance, same file
    nxt = b.append("result", {"order_ref": "x"})
    assert nxt["seq"] == last["seq"] + 1 and nxt["prev_hash"] == last["hash"]
    assert b.verify()["ok"]


def test_resume_is_robust_to_corrupt_tail(tmp_path):
    """A corrupt/partial last line must not reset the chain to genesis (which would
    duplicate seqs and break subsequent appends)."""
    p = str(tmp_path / "etl.jsonl")
    a = ExecutionTruthLedger(path=p)
    good = a.append("decision", {"order_ref": "x"})
    with open(p, "a", encoding="utf-8") as f:
        f.write('{"seq": 99, "partial-truncated-line\n')          # simulate a killed-process tail
    # New instance must resume from the last VALID record, not genesis.
    b = ExecutionTruthLedger(path=p)
    nxt = b.append("result", {"order_ref": "x"})
    assert nxt["seq"] == good["seq"] + 1, "must continue from last valid seq, not reset"
    assert nxt["prev_hash"] == good["hash"], "new append must chain from last valid record"


# ---- written-before-send / cannot-be-bypassed --------------------------------------

def test_decision_record_written_before_send(guard, ledger, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    order_state = {"sent": False, "decision_seen_at_send": None}

    def send_fn():
        # At send time the decision record must already be on disk.
        order_state["decision_seen_at_send"] = any(
            r["event"] == "decision" for r in ledger.read_all())
        order_state["sent"] = True
        return "OID-1"

    dec, oid = guard.authorize_and_send("bingx", _settings(False, True, False), _order(), send_fn, ledger=ledger)
    assert dec.mode is ExecutionMode.LIVE and oid == "OID-1"
    assert order_state["sent"] and order_state["decision_seen_at_send"] is True
    events = [r["event"] for r in ledger.read_all()]
    assert events == ["decision", "result"]


def test_blocked_order_still_writes_decision_record(guard, ledger):
    # No LIVE_TRADING + live endpoint -> BLOCKED, but the audit record must still exist.
    sent = {"v": False}
    def send_fn(): sent["v"] = True; return "X"
    dec, oid = guard.authorize_and_send("bingx", _settings(False, True, False), _order(), send_fn, ledger=ledger)
    assert dec.mode is ExecutionMode.BLOCKED and oid is None and sent["v"] is False
    recs = ledger.read_all()
    assert len(recs) == 1 and recs[0]["event"] == "decision" and recs[0]["route"] == "BLOCKED"


def test_paper_writes_decision_and_result_without_send(guard, ledger):
    sent = {"v": False}
    def send_fn(): sent["v"] = True; return "X"
    dec, oid = guard.authorize_and_send("bingx", _settings(True, True, False), _order(), send_fn, ledger=ledger)
    assert dec.mode is ExecutionMode.PAPER and oid.startswith("PAPER-") and sent["v"] is False
    recs = ledger.read_all()
    assert [r["event"] for r in recs] == ["decision", "result"]
    assert recs[1]["sent_to_exchange"] is False


def test_recorded_flags_match_decision(guard, ledger, monkeypatch):
    monkeypatch.setenv("LIVE_TRADING", "true")
    dec, oid = guard.authorize_and_send("bingx", _settings(False, True, False), _order(),
                                        lambda: "OID", ledger=ledger)
    rec = [r for r in ledger.read_all() if r["event"] == "decision"][0]
    assert rec["input_flags"] == dec.flags                       # ledger == exact decision inputs


# ---- concurrency: no race leaks a send outside allowed state -----------------------

def test_no_send_while_killed_or_breaker_open_under_chaos(guard, ledger):
    rng = random.Random(7)
    bc = SimpleNamespace(paper_trading=False, testnet=False, bingx_testnet=False,
                         bingx_order_placement_enabled=True)
    settings = SimpleNamespace(broker=bc)
    violations = []
    running = threading.Event(); running.set()

    def chaos():
        while running.is_set():
            bc.paper_trading = rng.random() < 0.25
            bc.bingx_testnet = rng.random() < 0.5
            bc.bingx_order_placement_enabled = rng.random() < 0.85
            os.environ["LIVE_TRADING"] = "true" if rng.random() < 0.5 else os.environ.pop("LIVE_TRADING", "")
            r = rng.random()
            if r < 0.05: guard.engage_kill_switch("chaos")
            elif r < 0.10: guard.disengage_kill_switch()

    def worker(wid):
        for k in range(120):
            o = SimpleNamespace(symbol=SimpleNamespace(value="BTC/USDT"), side=SimpleNamespace(name="BUY"))
            def send_fn():
                if guard.is_killed() or guard.breaker_blocks("bingx")[0]:
                    violations.append((wid, k))
                if rng.random() < 0.15:
                    raise RuntimeError("timeout")
                return f"OID-{wid}-{k}"
            try:
                guard.authorize_and_send("bingx", settings, o, send_fn, ledger=ledger)
            except Exception:
                pass

    ch = threading.Thread(target=chaos, daemon=True); ch.start()
    ts = [threading.Thread(target=worker, args=(w,)) for w in range(6)]
    for t in ts: t.start()
    for t in ts: t.join()
    running.clear(); ch.join(timeout=1); guard.disengage_kill_switch()
    os.environ.pop("LIVE_TRADING", None)

    # Invariant 1: no real send ever executed while killed or breaker-open.
    assert violations == [], f"race leaked sends while killed/breaker-open: {violations[:5]}"

    # Invariant 2: every LIVE send recorded was made under an allowed flag/state snapshot.
    recs = ledger.read_all()
    dec = {r["order_ref"]: r for r in recs if r["event"] == "decision"}
    live_sends = [r for r in recs if r["event"] == "result" and r.get("sent_to_exchange") and r["route"] == "LIVE"]
    for r in live_sends:
        d = dec[r["order_ref"]]
        assert d["input_flags"]["live_trading_env"] and not d["input_flags"]["paper_trading"]
        assert not d["input_flags"]["testnet_resolved"]
        assert not d["kill_switch"]["engaged"] and d["circuit_breaker"].get("state") != "open"

    # Invariant 3: the audit ledger is intact (tamper-evident chain).
    assert ledger.verify()["ok"]
