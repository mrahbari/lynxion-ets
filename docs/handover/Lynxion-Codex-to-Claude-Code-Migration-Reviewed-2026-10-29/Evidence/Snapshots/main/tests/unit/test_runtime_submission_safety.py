"""Failure injection for the runtime checkout's durable order boundary."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace

import pytest

from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.execution.live_order_journal import LiveOrderJournal


def test_initial_protection_identity_survives_entry_journal_restart(monkeypatch, tmp_path):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module
    path = str(tmp_path / "initial_protection.jsonl")
    journal = LiveOrderJournal(path)
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    def place(order):
        order.protective_order_ids = {"STOP_MARKET": "SL-1", "TAKE_PROFIT_MARKET": "TP-1"}
        return "ENTRY-1"
    service = _service(monkeypatch, SimpleNamespace(connected=True, place_order=place))
    monkeypatch.setattr(guard_module, "live_execution_guard", SimpleNamespace(
        evaluate=lambda *_args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **kwargs: (SimpleNamespace(allowed=True, simulate=False,
            mode=SimpleNamespace(value="testnet"), reason="synthetic"), kwargs["send_fn"]())))
    assert service.execute_order(_order()) == "ENTRY-1"
    record = LiveOrderJournal(path).in_flight()[0]
    assert record["status"] == "SUBMITTED" and record["order_id"] == "ENTRY-1"
    assert record["protective_order_ids"] == {"STOP_MARKET": "SL-1", "TAKE_PROFIT_MARKET": "TP-1"}
    assert "filled_qty" not in record

def test_intent_fsync_failure_is_not_reported_durable(monkeypatch, tmp_path):
    journal = LiveOrderJournal(str(tmp_path / "orders.jsonl"))

    def fail_fsync(_fd):
        raise OSError("disk write failed")

    monkeypatch.setattr("infrastructure.execution.live_order_journal.os.fsync", fail_fsync)
    with pytest.raises(OSError):
        journal.record_intent("BTCUSDT", "BUY", "1", "bingx")
    assert journal.in_flight() == []


def test_failed_lifecycle_write_retains_recoverable_memory(tmp_path):
    path = tmp_path / "orders.jsonl"
    journal = LiveOrderJournal(str(path))
    ref = journal.record_intent("BTCUSDT", "BUY", "1", "bingx")
    collision = tmp_path / "directory-not-journal"
    collision.mkdir()
    journal._path = str(collision)
    journal.record_failed(ref, "broker rejected")
    assert journal.in_flight()[0]["status"] == "INTENT"
    assert LiveOrderJournal(str(path)).in_flight()[0]["status"] == "INTENT"


def _service(monkeypatch, broker):
    from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService

    service = object.__new__(MultiBrokerExecutionService)
    service.logger = logging.getLogger("test_runtime_submission")
    service._settings = SimpleNamespace(
        execution=SimpleNamespace(prevent_same_direction_trade_per_symbol=False),
        broker=SimpleNamespace(bingx_order_placement_enabled=True,
                               binance_order_placement_enabled=False,
                               mexc_order_placement_enabled=False,
                               phemex_order_placement_enabled=False),
    )
    service.brokers = {"bingx": broker}
    service._order_map_lock = threading.RLock()
    service._order_exchange_map = {}
    service._send_order_placed_notification = lambda *_args: None
    service._enhance_order_with_risk_parameters = lambda order: order
    service._validate_order_risk = lambda order: True
    service._validate_order_parameters_before_broker = lambda order: True
    monkeypatch.setattr(
        "infrastructure.services.symbol_validator.symbol_validator.is_symbol_approved",
        lambda _symbol: True,
    )
    return service


def _order():
    return Order(symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("1"),
                 price=Money(Decimal("100"), "USDT"))


def test_failed_intent_write_blocks_send(monkeypatch, tmp_path):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module

    collision = tmp_path / "directory-not-journal"
    collision.mkdir()
    journal = LiveOrderJournal(str(collision))
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    calls = []
    service = _service(monkeypatch, SimpleNamespace(
        connected=True, place_order=lambda _order: calls.append("broker"),
    ))
    monkeypatch.setattr(guard_module, "live_execution_guard", SimpleNamespace(
        evaluate=lambda *_args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **_kwargs: calls.append("guard"),
    ))
    assert service.execute_order(_order()) is None
    assert calls == []
    assert journal.in_flight() == []


@pytest.mark.parametrize("response", ["timeout", "empty"])
def test_ambiguous_send_retains_intent(monkeypatch, tmp_path, response):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module

    journal = LiveOrderJournal(str(tmp_path / "orders.jsonl"))
    monkeypatch.setattr(journal_module, "live_order_journal", journal)

    def place(_order):
        if response == "timeout":
            raise TimeoutError("response lost")
        return None

    service = _service(monkeypatch, SimpleNamespace(connected=True, place_order=place))
    monkeypatch.setattr(guard_module, "live_execution_guard", SimpleNamespace(
        evaluate=lambda *_args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **kwargs: (
            SimpleNamespace(allowed=True, simulate=False,
                            mode=SimpleNamespace(value="testnet"), reason="fake approval"),
            kwargs["send_fn"](),
        ),
    ))
    order = _order()
    assert service.execute_order(order) is None
    rows = journal.in_flight()
    assert len(rows) == 1
    assert rows[0]["status"] == "INTENT"
    assert rows[0]["client_order_id"] == order.client_order_id


def test_acknowledged_send_persists_submitted_identity(monkeypatch, tmp_path):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module

    path = str(tmp_path / "orders.jsonl")
    journal = LiveOrderJournal(path)
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    service = _service(monkeypatch, SimpleNamespace(
        connected=True, place_order=lambda _order: "fake-order-id",
    ))
    monkeypatch.setattr(guard_module, "live_execution_guard", SimpleNamespace(
        evaluate=lambda *_args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **kwargs: (
            SimpleNamespace(allowed=True, simulate=False,
                            mode=SimpleNamespace(value="testnet"), reason="fake approval"),
            kwargs["send_fn"](),
        ),
    ))
    assert service.execute_order(_order()) == "fake-order-id"
    recovered = LiveOrderJournal(path).in_flight()
    assert len(recovered) == 1
    assert recovered[0]["status"] == "SUBMITTED"
    assert recovered[0]["order_id"] == "fake-order-id"


def test_unknown_intent_blocks_a_new_symbol_before_send(monkeypatch, tmp_path):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module

    journal = LiveOrderJournal(str(tmp_path / "orders.jsonl"))
    journal.record_intent("FETUSDT", "BUY", "1", "bingx")
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    calls = []
    service = _service(monkeypatch, SimpleNamespace(
        connected=True, place_order=lambda _order: calls.append("broker"),
    ))
    monkeypatch.setattr(guard_module, "live_execution_guard", SimpleNamespace(
        evaluate=lambda *_args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **_kwargs: calls.append("guard"),
    ))
    assert service.execute_order(_order()) is None
    assert calls == []
    assert len(journal.in_flight()) == 1


def test_concurrent_unknown_intent_admission_is_atomic(tmp_path):
    journal = LiveOrderJournal(str(tmp_path / "orders.jsonl"))
    barrier = threading.Barrier(2)

    def attempt(symbol):
        barrier.wait(timeout=5)
        try:
            journal.record_intent(symbol, "BUY", "1", "bingx")
            return "admitted"
        except RuntimeError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["BTCUSDT", "ETHUSDT"]))
    assert sorted(results) == ["admitted", "blocked"]
    assert len(journal.in_flight()) == 1


@pytest.mark.parametrize("status", ["INTENT", "SUBMITTED"])
@pytest.mark.parametrize("pending_result", ["empty", "error"])
def test_startup_preserves_unknown_lifecycle(monkeypatch, tmp_path, status, pending_result):
    from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService
    from infrastructure.execution import live_order_journal as journal_module

    path = tmp_path / "orders.jsonl"
    journal = LiveOrderJournal(str(path))
    ref = journal.record_intent("FETUSDT", "BUY", "1", "bingx", "fake-client")
    if status == "SUBMITTED":
        journal.record_submitted(ref, "fake-order", "bingx")
    before = path.read_bytes()
    monkeypatch.setattr(journal_module, "live_order_journal", journal)

    def pending():
        if pending_result == "error":
            raise TimeoutError("fake read failure")
        return []

    broker = SimpleNamespace(get_pending_orders=pending)
    monkeypatch.setattr(MultiBrokerExecutionService, "_initialize_brokers",
                        lambda service: service.brokers.update({"bingx": broker}))
    settings = SimpleNamespace(broker=SimpleNamespace(default_broker="bingx"))
    for _ in range(2):
        MultiBrokerExecutionService(settings)
        assert journal.in_flight()[0]["status"] == status
        assert LiveOrderJournal(str(path)).in_flight()[0]["status"] == status
        assert path.read_bytes() == before
