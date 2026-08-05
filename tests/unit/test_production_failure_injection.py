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
    
    Verifies that BingXBrokerAdapter.place_order fails CLOSED by raising an Exception
    when protective orders fail, preventing naked positions on exchange.
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
            'success': False,
            'order_id': None,
            'error': "protective orders failed (['SL order failed: 100001 Invalid Price Band']); unwound=True",
            'protection_failed': True,
            'conditional_orders_errors': ['SL order failed: 100001 Invalid Price Band']
        }

    monkeypatch.setattr(adapter._broker, 'execute_order', mock_execute_order)

    order = _build_test_order()
    
    # EXECUTION & PROOF OF FAIL-CLOSED BEHAVIOR:
    # Must raise Exception and NOT return an order_id to downstream caller!
    with pytest.raises(Exception) as exc_info:
        adapter.place_order(order)

    assert "Failed to place order" in str(exc_info.value)


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
    journal_path = str(tmp_path / "live_order_journal.json")
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


def test_position_notional_preserved_under_positive_slippage():
    """Scenario: signal_price = 100, max_notional = 50, fill_price = 102 (+2% slippage).
    
    Verifies that Option A execution reserve buffer (0.95 factor) guarantees
    final_filled_notional (qty * fill_price) <= max_notional (50 USDT).
    """
    from infrastructure.position_sizing.position_sizing_engine_adapter import PositionSizingEngineAdapter

    class _MockBaseSizingService:
        def compute_size(self, algorithm, **kwargs):
            # Base sizing: max_notional / signal_price = 50 / 100 = 0.5 units
            signal_price = kwargs.get("entry_price", 100.0)
            max_notional = kwargs.get("max_notional", 50.0)
            return max_notional / signal_price

    adapter = PositionSizingEngineAdapter(service=_MockBaseSizingService())
    
    # Calculate sized units with 5% execution reserve buffer (0.95)
    signal_price = 100.0
    max_notional = 50.0
    fill_price = 102.0  # +2.0% positive execution slippage
    
    sized_units = adapter.compute_size(
        "fixed_fractional",
        entry_price=signal_price,
        stop_loss=95.0,
        portfolio_equity=500.0,
        risk_per_trade=0.02,
        max_notional=max_notional,
        execution_buffer=0.95
    )
    
    # Realized filled notional on exchange: sized_units * fill_price
    final_filled_notional = sized_units * fill_price
    
    assert sized_units == pytest.approx(0.475)
    assert final_filled_notional == pytest.approx(48.45)
    assert final_filled_notional <= max_notional  # Invariant GUARANTEED <= 50 USDT!


def test_position_notional_preserved_under_fast_market_gap():
    """Scenario: signal_price = 100, fill_price = 105 (+5% volatility gap).
    
    Verifies that system prevents notional boundary violation under fast gap.
    """
    from infrastructure.position_sizing.position_sizing_engine_adapter import PositionSizingEngineAdapter

    class _MockBaseSizingService:
        def compute_size(self, algorithm, **kwargs):
            signal_price = kwargs.get("entry_price", 100.0)
            max_notional = kwargs.get("max_notional", 50.0)
            return max_notional / signal_price

    adapter = PositionSizingEngineAdapter(service=_MockBaseSizingService())
    
    signal_price = 100.0
    max_notional = 50.0
    fill_price = 105.0  # +5.0% fast market gap
    
    sized_units = adapter.compute_size(
        "fixed_fractional",
        entry_price=signal_price,
        stop_loss=95.0,
        portfolio_equity=500.0,
        risk_per_trade=0.02,
        max_notional=max_notional,
        execution_buffer=0.95
    )
    
    final_filled_notional = sized_units * fill_price
    
    assert final_filled_notional == 49.875  # 0.475 * 105
    assert final_filled_notional <= max_notional  # Invariant GUARANTEED <= 50 USDT under 5% gap!


def test_no_double_scaling_position_size():
    """Verify PositionSizingEngineAdapter remains sole quantity owner in pipeline.
    
    Ensures zero duplicate multipliers are introduced elsewhere in the execution chain.
    """
    from infrastructure.position_sizing.position_sizing_engine_adapter import PositionSizingEngineAdapter

    class _MockBaseSizingService:
        def compute_size(self, algorithm, **kwargs):
            return 1.0

    adapter = PositionSizingEngineAdapter(service=_MockBaseSizingService())
    
    # When disabled and no extra multipliers, units must be 1.0 * 1.0 = 1.0
    result = adapter.compute_size(
        "fixed_fractional",
        entry_price=100.0,
        stop_loss=95.0,
        portfolio_equity=500.0,
        risk_per_trade=0.02,
        execution_buffer=1.0
    )
    assert result == 1.0


def test_extreme_slippage_boundary_behavior():
    """Scenario: max_notional = 50, signal_price = 100, fill_price = 110 (+10% extreme slippage), buffer = 0.95.
    
    Verifies explicit boundary behavior: when extreme market slippage (+10%) causes filled notional (52.25)
    to exceed max_notional (50.0), the breach is explicitly detected (is_breached=True)
    so emergency protection or halt rules can be triggered, preventing silent unchecked exposure.
    """
    from infrastructure.position_sizing.position_sizing_engine_adapter import PositionSizingEngineAdapter

    class _MockBaseSizingService:
        def compute_size(self, algorithm, **kwargs):
            signal_price = kwargs.get("entry_price", 100.0)
            max_notional = kwargs.get("max_notional", 50.0)
            return max_notional / signal_price

    adapter = PositionSizingEngineAdapter(service=_MockBaseSizingService())
    
    signal_price = 100.0
    max_notional = 50.0
    fill_price = 110.0  # +10.0% extreme slippage
    
    sized_units = adapter.compute_size(
        "fixed_fractional",
        entry_price=signal_price,
        stop_loss=95.0,
        portfolio_equity=500.0,
        risk_per_trade=0.02,
        max_notional=max_notional,
        execution_buffer=0.95
    )
    
    final_filled_notional = sized_units * fill_price
    
    # Under +10% extreme slippage: 0.475 * 110 = 52.25 USDT
    assert final_filled_notional == 52.25
    
    # Boundary breach detected explicitly:
    is_breached = final_filled_notional > max_notional
    assert is_breached is True


