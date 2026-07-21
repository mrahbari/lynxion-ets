"""
Production Failure Injection Campaign Tests (Task 0044 / Production Adversarial Audit).

Executes:
- Scenario A: SL/TP Conditional Order Failure Injection
- Scenario B: Quantity Rounding & Step-Size Boundary Failure Injection
- Scenario C: Crash Between Entry Fill & SL Failure + Reconciliation Audit
"""
import math
import logging
from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest

from domain.entities import Order, OrderSide
from domain.value_objects import Money, Symbol
from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter, _BingXBroker
from infrastructure.execution.live_order_journal import LiveOrderJournal
from infrastructure.execution.broker_reconciliation import BrokerReconciliationService


def _build_test_order(symbol="BTC-USDT", side=OrderSide.BUY, qty="0.0156", sl="58000"):
    return Order(
        symbol=Symbol(symbol),
        side=side,
        quantity=Decimal(qty),
        price=Money(Decimal("60000"), "USDT"),
        order_type="MARKET",
        stop_loss_price=Money(Decimal(sl), "USDT") if sl else None,
        timestamp=datetime.now(timezone.utc)
    )


def test_scenario_a_sltp_failure_injection(monkeypatch):
    """Scenario A: Entry order accepted by exchange, but attached SL order fails.
    
    Verifies that BingXBrokerAdapter.place_order fails OPEN by logging a warning
    and returning the main order_id as SUCCESS, leaving a Naked Long on exchange.
    """
    adapter = BingXBrokerAdapter(config={
        'api_key': 'test_key',
        'secret_key': 'test_secret',
        'base_url': 'https://open-api.bingx.com'
    })
    adapter.connected = True

    # Mock internal _broker.execute_order to simulate BingX returning SL failure
    def mock_execute_order(temp_order):
        return {
            'success': True,
            'order_id': 'MAIN_BINGX_OID_999',
            'conditional_orders_errors': ['SL order failed: 100001 Invalid Price Band']
        }

    monkeypatch.setattr(adapter._broker, 'execute_order', mock_execute_order)

    order = _build_test_order()
    
    # EXECUTION: Call place_order
    # EXPECTED SAFE BEHAVIOR: Raise Exception / Cancel main order
    # ACTUAL BEHAVIOR: Returns order_id successfully despite failed SL!
    returned_order_id = adapter.place_order(order)

    assert returned_order_id == 'MAIN_BINGX_OID_999'
    # PROOF: Main entry order is returned as SUCCESS to caller, leaving Naked Position on BingX!


def test_scenario_b_quantity_rounding_failure_injection():
    """Scenario B: Quantity formatting near rounding boundaries.
    
    Verifies that _format_quantity uses IEEE 754 half-up rounding (f'{qty:.3f}')
    rather than math.floor step-size clamping, leading to step-size violations.
    """
    broker = object.__new__(_BingXBroker)
    broker._contract_precisions = {
        'BTC-USDT': {'pricePrecision': 2, 'quantityPrecision': 3},
        'ETH-USDT': {'pricePrecision': 2, 'quantityPrecision': 3},
        'SOL-USDT': {'pricePrecision': 3, 'quantityPrecision': 2},
        'XRP-USDT': {'pricePrecision': 4, 'quantityPrecision': 1},
    }

    # Case 1: 0.0156 BTC -> quantityPrecision=3 -> f"{0.0156:.3f}" = "0.016" (Rounds UP)
    fmt_btc = broker._format_quantity('BTC-USDT', 0.0156)
    assert fmt_btc == "0.016"
    
    # Prove exposure increase: 0.016 vs 0.0156 is a +2.56% exposure inflation!
    diff_pct = (float(fmt_btc) - 0.0156) / 0.0156 * 100.0
    assert diff_pct > 2.0  # +2.56% unintended risk inflation

    # Case 2: 0.0999 XRP -> quantityPrecision=1 -> f"{0.0999:.1f}" = "0.1" (Rounds UP)
    fmt_xrp = broker._format_quantity('XRP-USDT', 0.0999)
    assert fmt_xrp == "0.1"


def test_scenario_c_crash_between_events_and_reconciliation(tmp_path):
    """Scenario C: Entry accepted, SL creation fails, process crashes, restart system.
    
    Verifies restart behavior and BrokerReconciliationService detection.
    """
    journal_path = str(tmp_path / "live_order_journal.jsonl")
    journal = LiveOrderJournal(path=journal_path)

    # 1. Strategy records intent and order submission before crash
    ref = journal.record_intent("BTC-USDT", "BUY", "0.016", "bingx", "x123")
    journal.record_submitted(ref, "MAIN_BINGX_OID_999", "bingx")

    # 2. Process crashes and restarts
    restarted_journal = LiveOrderJournal(path=journal_path)
    recovery_stats = restarted_journal.recover()
    
    assert recovery_stats["total_orders"] >= 1
    in_flight = restarted_journal.in_flight()
    assert len(in_flight) == 1
    assert in_flight[0]["order_id"] == "MAIN_BINGX_OID_999"

    # 3. Reconcile against broker state
    class _MockCrashBroker:
        def get_all_positions(self):
            return [SimpleNamespace(symbol=Symbol("BTC-USDT"), quantity=0.016, side=SimpleNamespace(value="LONG"))]
        def get_order_status(self, order_id, symbol):
            return "FILLED"

    halts = []
    reconciler = BrokerReconciliationService(halt_fn=halts.append)
    report = reconciler.reconcile(_MockCrashBroker(), restarted_journal)

    # Reconciler resolves filled in-flight order
    assert report["halted"] is False
    assert len(restarted_journal.in_flight()) == 0
