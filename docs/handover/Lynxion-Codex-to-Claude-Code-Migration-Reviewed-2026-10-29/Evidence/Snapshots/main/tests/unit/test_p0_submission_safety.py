"""Offline failure injection for the main-branch VST submission path."""

import logging
import threading
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace
import pytest
import requests

from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService
from infrastructure.execution.live_order_journal import LiveOrderJournal

@pytest.mark.parametrize("content", ['{broken-json}\n', '[]\n', '{}\n', '{"order_ref":"r"}\n', '{"order_ref":"r","status":"TYPO"}\n', '{"order_ref":7,"status":"INTENT"}\n', '{"order_ref":" ","status":"INTENT"}\n'])
def test_corrupt_journal_blocks_recovery_and_append(tmp_path, content):
    path = tmp_path / "journal.jsonl"
    path.write_text(content, encoding="utf-8")
    journal = LiveOrderJournal(str(path))
    with pytest.raises(RuntimeError, match="journal integrity"):
        journal.recover()
    with pytest.raises(RuntimeError, match="journal integrity"):
        journal.record_intent("BTCUSDT", "BUY", 1, "fake")
    assert path.read_text(encoding="utf-8") == content

def test_missing_journal_is_valid_empty_state(tmp_path):
    journal = LiveOrderJournal(str(tmp_path / "absent.jsonl"))
    assert journal.recover()["total_orders"] == 0

@pytest.mark.parametrize("auto_detect", [False, True])
@pytest.mark.parametrize("mode,status,blocked", [
    ("TESTNET", "INTENT", True), ("TESTNET", "PROTECTION_UNKNOWN", True),
    ("LIVE", "INTENT", True), ("LIVE", "PROTECTION_UNKNOWN", True),
    ("TESTNET", "READ_FAILURE", True), ("TESTNET", "INVALID_SUMMARY", True),
    ("TESTNET", "SUBMITTED", False), ("PAPER", "PROTECTION_UNKNOWN", False)])
def test_production_startup_preserves_unknown_recovery_gate(monkeypatch, mode, status, blocked, auto_detect):
    from interface.cli import trading_system_production as cli
    from bootstrap.settings import loaders
    from shared import preflight
    import infrastructure.execution.live_order_journal as journal_module
    @contextmanager
    def fake_lifespan():
        yield SimpleNamespace(resolve=lambda name: object())
    started = []
    monkeypatch.setattr(cli, "lifespan", fake_lifespan)
    monkeypatch.setattr(loaders, "load_settings", lambda: object())
    monkeypatch.setattr(preflight, "run_preflight", lambda settings: {
        "mode": mode, "ok": True, "flags": {}, "warnings": [], "blocking": []})
    def recover():
        if status == "READ_FAILURE":
            raise OSError("synthetic journal read unavailable")
        return {"status_counts": None if status == "INVALID_SUMMARY" else {status: 1}}
    monkeypatch.setattr(journal_module, "live_order_journal", SimpleNamespace(recover=recover))
    monkeypatch.setattr(cli, "RunLiveTradingUseCase", lambda **kwargs: SimpleNamespace(
        run=lambda **run_kwargs: started.append("started") or 0))
    monkeypatch.setattr(cli, "RunAutoDetectionUseCase", lambda **kwargs: SimpleNamespace(
        run=lambda **run_kwargs: started.append("started") or 0))
    assert cli.main(["--mode", "production"] + (["--auto-detect"] if auto_detect else [])) == (2 if blocked else 0)
    assert started == ([] if blocked else ["started"])

@pytest.mark.parametrize("persist_ack", [True, False])
def test_manager_protective_ack_persistence_controls_restart(tmp_path, monkeypatch, persist_ack):
    from infrastructure.risk.active_position_manager import ActivePositionManager
    import infrastructure.execution.live_order_journal as journal_module
    path = str(tmp_path / "ack_protection.jsonl")
    journal = LiveOrderJournal(path=path)
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    if not persist_ack:
        monkeypatch.setattr(journal, "record_submitted", lambda *args: None)
    calls = []
    broker = SimpleNamespace(name="bingx", _place_conditional_order=lambda **kwargs: calls.append(kwargs) or {
        "success": True, "order_id": "ACK-SL"})
    manager = object.__new__(ActivePositionManager)
    manager._positions_state = {}
    manager._sync_sl_to_exchange(broker, "ADAUSDT", True, 1, 10)
    restored = LiveOrderJournal(path=path)
    record = restored.in_flight()[0]
    assert record["status"] == ("SUBMITTED" if persist_ack else "PROTECTION_UNKNOWN")
    assert record["stop_price"] == "10" and record["entry_order_ref"] is None
    if persist_ack:
        assert restored.order_exchange_map() == {"ACK-SL": ("bingx", "ADA-USDT")}
        assert restored.record_intent("ETH-USDT", "BUY", "1", "bingx")
    else:
        monkeypatch.setattr(journal_module, "live_order_journal", restored)
        restarted = object.__new__(ActivePositionManager)
        restarted._positions_state = {}
        restarted._sync_sl_to_exchange(broker, "ADAUSDT", True, 1, 10)
    assert len(calls) == 1

def test_manager_restart_cannot_resubmit_unknown_protection(tmp_path, monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager
    import infrastructure.execution.live_order_journal as journal_module
    path = str(tmp_path / "durable_protection.jsonl")
    monkeypatch.setattr(journal_module, "live_order_journal", LiveOrderJournal(path=path))
    calls = []
    broker = SimpleNamespace(_place_conditional_order=lambda **kwargs: calls.append(kwargs) or {
        "success": False, "unknown_submission": True, "error": "synthetic lost ack"})
    first = object.__new__(ActivePositionManager)
    first._positions_state = {}
    first._sync_sl_to_exchange(broker, "ADAUSDT", True, 1, 10)
    monkeypatch.setattr(journal_module, "live_order_journal", LiveOrderJournal(path=path))
    second = object.__new__(ActivePositionManager)
    second._positions_state = {}
    second._sync_sl_to_exchange(broker, "ADAUSDT", True, 1, 10)
    assert len(calls) == 1
    assert journal_module.live_order_journal.in_flight()[0]["status"] == "PROTECTION_UNKNOWN"

def test_manager_protection_write_failure_prevents_all_broker_actions(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager
    import infrastructure.execution.live_order_journal as journal_module
    def fail_write(*args, **kwargs):
        raise OSError("synthetic disk unavailable")
    monkeypatch.setattr(journal_module, "live_order_journal", SimpleNamespace(
        in_flight=lambda: [], record_protection_unknown=fail_write))
    calls = []
    broker = SimpleNamespace(get_pending_orders=lambda *args: calls.append("read") or [],
        cancel_order=lambda *args: calls.append("cancel"),
        _place_conditional_order=lambda **kwargs: calls.append("send") or {"success": True, "order_id": "ACK"})
    manager = object.__new__(ActivePositionManager)
    manager._positions_state = {}
    manager._sync_sl_to_exchange(broker, "ADAUSDT", True, 1, 10)
    assert calls == []

@pytest.mark.parametrize("snapshot", ["flat", "missing", "exception"])
def test_manager_cleanup_never_erases_unknown_protection(snapshot):
    from infrastructure.risk.active_position_manager import ActivePositionManager
    manager = object.__new__(ActivePositionManager)
    unknown = {"broker_sl_state": "UNKNOWN", "broker_sl_request": {"stop_price": "10"}}
    known = {"broker_sl_state": "KNOWN"}
    manager._positions_state = {"ADAUSDT": unknown, "BTCUSDT": known}
    def positions():
        if snapshot == "exception":
            raise TimeoutError("synthetic missing snapshot")
        return None if snapshot == "missing" else []
    broker = SimpleNamespace(get_all_positions=positions)
    assert manager.evaluate_open_positions(broker) == []
    assert manager._positions_state["ADAUSDT"] is unknown
    if snapshot == "flat":
        assert "BTCUSDT" not in manager._positions_state
    else:
        assert manager._positions_state["BTCUSDT"] is known

@pytest.mark.parametrize("failure", ["missing_id", "timeout", "direct_exception"])
def test_manager_never_retries_unknown_conditional_submission(tmp_path, monkeypatch, failure):
    import infrastructure.execution.live_order_journal as journal_module
    monkeypatch.setattr(journal_module, "live_order_journal", LiveOrderJournal(
        path=str(tmp_path / "isolated_manager.jsonl")))
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
    from infrastructure.risk.active_position_manager import ActivePositionManager
    manager = object.__new__(ActivePositionManager)
    manager._positions_state = {}
    broker = object.__new__(_BingXBroker)
    broker._format_symbol_str = lambda value: value
    broker._format_price = lambda symbol, value: str(value)
    broker._format_quantity = lambda symbol, value: str(value)
    broker.logger = logging.getLogger("synthetic_manager_unknown")
    cancellations = []
    broker.get_pending_orders = lambda *args: cancellations.append("read") or []
    posts = []
    def request(*args, **kwargs):
        posts.append((args, kwargs))
        if failure == "timeout":
            raise TimeoutError("synthetic accepted response lost")
        return {"code": 0, "data": {"order": {}}}
    broker._make_request = request
    if failure == "direct_exception":
        def fail_directly(**kwargs):
            posts.append(kwargs)
            raise TimeoutError("synthetic accepted response lost")
        broker._place_conditional_order = fail_directly
    monkeypatch.setattr("infrastructure.risk.active_position_manager.time.sleep", lambda *args: None)
    manager._sync_sl_to_exchange(broker, "ADAUSDT", True, 1, 10)
    assert len(posts) == 1
    assert manager._positions_state["ADAUSDT"]["broker_sl_state"] == "UNKNOWN"
    manager._sync_sl_to_exchange(broker, "ADAUSDT", True, 1, 11)
    assert len(posts) == 1 and cancellations == ["read"]

@pytest.mark.parametrize("order_id,expected", [(None, False), ("", False), ("ACK-1", True)])
def test_conditional_ack_identity_controls_known_protection(order_id, expected):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
    broker = object.__new__(_BingXBroker)
    broker._format_symbol_str = lambda value: value
    broker._format_price = lambda symbol, value: str(value)
    broker._format_quantity = lambda symbol, value: str(value)
    broker.logger = logging.getLogger("synthetic_conditional_identity")
    requests_seen = []
    def response(*args, **kwargs):
        requests_seen.append((args, kwargs))
        return {"code": 0, "data": {"order": {"orderId": order_id}}}
    broker._make_request = response
    result = broker._place_conditional_order("ADA-USDT", "SELL", "1", "10", "STOP_MARKET", "LONG")
    assert result["success"] is expected
    if not expected:
        assert result["unknown_submission"] is True
    else:
        assert result["order_id"] == "ACK-1"
    assert len(requests_seen) == 1

@pytest.mark.parametrize("bad_row", [None, {}, {"positionAmt": "bad"},
    {"positionAmt": "NaN", "symbol": "BTC-USDT", "avgPrice": "10"}, {"positionAmt": "Infinity", "symbol": "BTC-USDT", "avgPrice": "10"},
    {"positionAmt": "1", "symbol": "BTC-USDT"}])
@pytest.mark.parametrize("valid_prefix", [False, True])
def test_malformed_position_row_never_returns_partial_snapshot(bad_row, valid_prefix):
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
    adapter = object.__new__(BingXBrokerAdapter)
    adapter.connected = True
    adapter.logger = logging.getLogger("synthetic_positions")
    adapter._parse_symbol = Symbol
    valid = {"positionAmt": "1", "symbol": "BTC-USDT", "avgPrice": "10"}
    rows = ([valid] if valid_prefix else []) + [bad_row]
    adapter._broker = SimpleNamespace(get_open_positions=lambda: rows)
    with pytest.raises(RuntimeError, match="position snapshot"):
        adapter.get_all_positions()

def test_valid_position_and_zero_quantity_row_are_preserved():
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
    adapter = object.__new__(BingXBrokerAdapter)
    adapter.connected = True
    adapter._parse_symbol = Symbol
    adapter._broker = SimpleNamespace(get_open_positions=lambda: [
        {"positionAmt": "0"}, {"positionAmt": "-2", "symbol": "BTC-USDT", "avgPrice": "10"}])
    result = adapter.get_all_positions()
    assert len(result) == 1 and result[0].quantity == 2
    assert result[0].side.value == "SHORT"

@pytest.mark.parametrize("response", [None, {"code": 100001}, {"code": 0}, {"code": 0, "data": {}}])
def test_unavailable_bingx_position_response_is_not_flat(response):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
    broker = object.__new__(_BingXBroker)
    broker._make_request = lambda *args, **kwargs: response
    with pytest.raises(RuntimeError):
        broker.get_open_positions()

def test_bingx_position_transport_failure_propagates():
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
    broker = object.__new__(_BingXBroker)
    def fail(*args, **kwargs):
        raise TimeoutError("synthetic timeout")
    broker._make_request = fail
    with pytest.raises(TimeoutError):
        broker.get_open_positions()

def test_successful_empty_bingx_position_snapshot_is_flat():
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
    broker = object.__new__(_BingXBroker)
    broker._make_request = lambda *args, **kwargs: {"code": 0, "data": []}
    assert broker.get_open_positions() == []

def test_duplicate_queued_intent_is_rejected_before_shared_order_tracking():
    from infrastructure.orchestrators._auto_detection_dedup import _AutoDetectionDedupMixin

    owner = _AutoDetectionDedupMixin()
    owner._settings = SimpleNamespace(execution=SimpleNamespace(
        prevent_same_direction_trade_per_symbol=True))
    owner._pending_intents_lock = threading.RLock()
    owner._pending_intents = {}
    owner._pending_intent_temp_ids = {}
    owner._pending_orders_tracker = SimpleNamespace(
        get_pending_orders_for_symbol=lambda symbol: [])
    owner._execution_now = lambda: 1
    owner.logger = SimpleNamespace(info=lambda *args: None)
    first = SimpleNamespace(symbol=SimpleNamespace(value="XRPUSDT"),
                            side=SimpleNamespace(name="BUY"))
    repeated = SimpleNamespace(symbol=SimpleNamespace(value="XRPUSDT"),
                               side=SimpleNamespace(name="BUY"))

    assert owner._check_duplicate_execution_intent(first) is False
    assert owner._check_duplicate_execution_intent(repeated) is True
    owner._remove_pending_execution_intent(first)
    assert owner._check_duplicate_execution_intent(repeated) is False


def test_cooldown_dropped_queue_item_releases_pending_identity(monkeypatch):
    from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
    import infrastructure.risk.symbol_cooldown_gate as gate_module

    owner = object.__new__(AutoDetectionOrchestrator)
    intent = SimpleNamespace(symbol=SimpleNamespace(value="XRPUSDT"),
                             side=SimpleNamespace(name="BUY"))
    owner.is_running = True
    owner.opportunity_queue = [intent]
    owner._opportunity_queue_lock = threading.RLock()
    owner._pending_intents_lock = threading.RLock()
    owner._pending_intents = {"XRPUSDT": {"BUY": 1}}
    owner._pending_intent_temp_ids = {id(intent): None}
    owner._pending_orders_tracker = SimpleNamespace(remove_pending_order=lambda *args: None)
    owner.logger = SimpleNamespace(info=lambda *args: None, debug=lambda *args: None,
                                   error=lambda *args: None)

    def deny_once(_symbol):
        owner.is_running = False
        return False, "cooldown"

    monkeypatch.setattr(gate_module.symbol_cooldown_gate, "is_symbol_allowed", deny_once)
    owner._opportunity_processing_loop()
    assert owner.opportunity_queue == []
    assert owner._pending_intents == {}
    assert owner._pending_intent_temp_ids == {}


@pytest.mark.parametrize("preflight_result", ["exception", "blocked_testnet"])
def test_production_cli_does_not_start_when_preflight_fails(monkeypatch, preflight_result):
    from interface.cli import trading_system_production as cli
    from bootstrap.settings import loaders
    from shared import preflight

    @contextmanager
    def fake_lifespan():
        yield SimpleNamespace(resolve=lambda name: object())

    started = []
    monkeypatch.setattr(cli, "lifespan", fake_lifespan)
    monkeypatch.setattr(loaders, "load_settings", lambda: object())
    monkeypatch.setattr(
        cli, "RunLiveTradingUseCase",
        lambda **kwargs: SimpleNamespace(run=lambda **run_kwargs: started.append(run_kwargs) or 0),
    )
    if preflight_result == "exception":
        monkeypatch.setattr(preflight, "run_preflight", lambda settings: (_ for _ in ()).throw(RuntimeError("bad preflight")))
    else:
        monkeypatch.setattr(preflight, "run_preflight", lambda settings: {
            "mode": "TESTNET", "ok": False, "flags": {}, "warnings": [],
            "blocking": ["missing VST configuration"],
        })

    assert cli.main(["--mode", "production"]) == 2
    assert started == []


@pytest.mark.parametrize("protected", [False, True])
def test_bingx_market_order_uses_documented_client_order_id_key(protected):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("p0_bingx_order_identity")
    broker._format_quantity = lambda symbol, quantity: str(quantity)
    broker._format_price = lambda symbol, price: str(price)
    broker._place_conditional_order = lambda **kwargs: {"success": True, "order_id": "stop"}
    sent = []
    broker._make_request = lambda method, endpoint, params=None, data=None, signed=False: (
        sent.append((method, endpoint, data)),
        {"code": 0, "data": {"order": {"orderId": "isolated-order"}}},
    )[1]
    order = SimpleNamespace(
        symbol="BTC-USDT", side="BUY", order_type="MARKET", quantity=Decimal("1"),
        position_side="LONG", price=None,
        stop_loss_price=Decimal("95") if protected else None,
        take_profit_price=None,
        client_order_id="isolated-client",
    )

    result = broker.execute_order(order)
    assert result["success"] is True
    assert len(sent) == 1
    assert sent[0][2]["clientOrderId"] == "isolated-client"
    assert "clientOrderID" not in sent[0][2]


@pytest.mark.parametrize("position_response,expected", [
    ({"code": 0, "data": [{"symbol": "BTC-USDT", "positionAmt": "1"}]}, False),
    ({"code": 0, "data": [{"symbol": "BTC-USDT", "positionAmt": "0"}]}, True),
    ({"code": 100001, "msg": "position query failed"}, False),
])
def test_unwind_ack_requires_flat_broker_snapshot(position_response, expected):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("p0_unwind_snapshot")
    calls = []

    def request(method, endpoint, params=None, data=None, signed=False):
        calls.append(method)
        if method == "POST":
            return {"code": 0, "data": {"order": {"orderId": "close-accepted"}}}
        return position_response

    broker._make_request = request
    assert broker._unwind_position("BTC-USDT", "BUY", "1", "LONG") is expected
    assert calls == ["POST", "GET"]


def test_conditional_conflict_never_cancels_existing_stop_or_resubmits():
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("p0_conditional_conflict")
    broker._format_price = lambda symbol, price: str(price)
    broker._format_quantity = lambda symbol, quantity: str(quantity)
    requests_seen = []
    broker._make_request = lambda *args, **kwargs: (
        requests_seen.append((args, kwargs)),
        {"code": 110406, "msg": "position SL already exists"},
    )[1]
    broker.get_pending_orders = lambda symbol: [{"type": "STOP_MARKET", "orderId": "existing-stop"}]
    cancelled = []
    broker.cancel_order = lambda order_id, symbol: cancelled.append((order_id, symbol))

    result = broker._place_conditional_order(
        "BTC-USDT", "SELL", "1", "95", "STOP_MARKET", "LONG"
    )
    assert result["success"] is False
    assert len(requests_seen) == 1
    assert cancelled == []


@pytest.mark.parametrize("order_type", ["MARKET", "STOP_MARKET", "TAKE_PROFIT_MARKET"])
def test_bingx_order_post_timeout_is_not_blindly_retried(order_type):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    attempts = []

    def lost_response(*args, **kwargs):
        attempts.append((args, kwargs))
        raise requests.exceptions.Timeout("response lost")

    broker = object.__new__(_BingXBroker)
    broker.base_url = "https://example.invalid"
    broker.api_key = "isolated-test-key"
    broker.secret_key = "isolated-test-secret"
    broker.default_timeout = 1
    broker.logger = logging.getLogger("p0_bingx_retry")
    broker.session = SimpleNamespace(post=lost_response)
    broker._rate_limit = lambda: None

    with pytest.raises(requests.exceptions.Timeout):
        broker._make_request(
            "POST", "/openApi/swap/v2/trade/order",
            data={"symbol": "BTC-USDT", "type": order_type}, signed=True,
        )
    assert len(attempts) == 1


def test_bingx_non_order_post_retains_transient_retry():
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    attempts = []

    def transient(*args, **kwargs):
        attempts.append((args, kwargs))
        if len(attempts) == 1:
            raise requests.exceptions.Timeout("response lost")
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"code": 0})

    broker = object.__new__(_BingXBroker)
    broker.base_url = "https://example.invalid"
    broker.api_key = "isolated-test-key"
    broker.secret_key = "isolated-test-secret"
    broker.default_timeout = 1
    broker.logger = logging.getLogger("p0_bingx_non_order_retry")
    broker.session = SimpleNamespace(post=transient)
    broker._rate_limit = lambda: None

    result = broker._make_request(
        "POST", "/openApi/swap/v2/trade/leverage", data={"symbol": "BTC-USDT"}, signed=True
    )
    assert result["code"] == 0
    assert len(attempts) == 2


def _order():
    return Order(
        symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("1"),
        price=Money(Decimal("100"), "USDT"),
        stop_loss_price=Money(Decimal("95"), "USDT"),
        take_profit_price=Money(Decimal("110"), "USDT"),
    )


def _service(monkeypatch, broker):
    service = object.__new__(MultiBrokerExecutionService)
    service.logger = logging.getLogger("p0_submission_safety")
    service._settings = SimpleNamespace(
        execution=SimpleNamespace(prevent_same_direction_trade_per_symbol=False),
        broker=SimpleNamespace(bingx_order_placement_enabled=True,
                               binance_order_placement_enabled=False,
                               mexc_order_placement_enabled=False,
                               phemex_order_placement_enabled=False),
    )
    service.brokers = {"bingx": broker}
    monkeypatch.setattr(service, "_enhance_order_with_risk_parameters", lambda order: order)
    monkeypatch.setattr(service, "_validate_order_risk", lambda order: True)
    monkeypatch.setattr(service, "_validate_order_parameters_before_broker", lambda order: True)
    monkeypatch.setattr(
        "infrastructure.services.symbol_validator.symbol_validator.is_symbol_approved",
        lambda symbol: True,
    )
    return service


def test_presend_intent_failure_never_calls_broker_or_guard(monkeypatch, tmp_path):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module

    send_attempts = []
    service = _service(monkeypatch, SimpleNamespace(
        connected=True, place_order=lambda order: send_attempts.append(order)
    ))
    collision = tmp_path / "journal-path-is-a-directory"
    collision.mkdir()
    journal = LiveOrderJournal(path=str(collision))
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    guard_calls = []
    guard = SimpleNamespace(
        evaluate=lambda *args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **kwargs: guard_calls.append(kwargs),
    )
    monkeypatch.setattr(guard_module, "live_execution_guard", guard)

    assert service.execute_order(_order()) is None
    assert guard_calls == []
    assert send_attempts == []
    assert journal.in_flight() == []


def test_existing_unknown_intent_blocks_new_real_send(monkeypatch, tmp_path):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module

    journal = LiveOrderJournal(path=str(tmp_path / "orders.jsonl"))
    journal.record_intent("FETUSDT", "BUY", "1", "bingx", "unknown-client")
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    send_attempts = []
    service = _service(monkeypatch, SimpleNamespace(
        connected=True, place_order=lambda order: send_attempts.append(order)
    ))
    guard_calls = []
    guard = SimpleNamespace(
        evaluate=lambda *args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **kwargs: guard_calls.append(kwargs),
    )
    monkeypatch.setattr(guard_module, "live_execution_guard", guard)

    assert service.execute_order(_order()) is None
    assert guard_calls == []
    assert send_attempts == []
    assert len(journal.in_flight()) == 1


@pytest.mark.parametrize("broker_response", ["timeout", "empty"])
def test_unknown_after_send_keeps_intent_for_reconciliation(
    monkeypatch, tmp_path, broker_response
):
    from infrastructure.execution import live_order_journal as journal_module
    from shared import live_execution_guard as guard_module

    def broker_place_order(order):
        if broker_response == "timeout":
            raise TimeoutError("response lost")
        return None

    service = _service(monkeypatch, SimpleNamespace(
        connected=True, place_order=broker_place_order
    ))
    journal = LiveOrderJournal(path=str(tmp_path / "orders.jsonl"))
    monkeypatch.setattr(journal_module, "live_order_journal", journal)
    guard = SimpleNamespace(
        evaluate=lambda *args: SimpleNamespace(is_real_send=True),
        authorize_and_send=lambda **kwargs: (
            SimpleNamespace(allowed=True, simulate=False, mode=SimpleNamespace(value="testnet"),
                            reason="test authorized"),
            kwargs["send_fn"](),
        ),
    )
    monkeypatch.setattr(guard_module, "live_execution_guard", guard)
    order = _order()

    assert service.execute_order(order) is None
    inflight = journal.in_flight()
    assert len(inflight) == 1
    assert inflight[0]["status"] == "INTENT"
    assert inflight[0]["client_order_id"] == order.client_order_id
