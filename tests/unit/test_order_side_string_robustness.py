"""Unit tests to verify order side string robustness across all broker adapters.

Ensures that order side is correctly parsed and recognized as BUY/SELL or LONG/SHORT
even when passed as raw strings (e.g. from journal/database recovery).
"""

from decimal import Decimal
import logging
import pytest

from domain.entities import Order, OrderSide
from domain.value_objects import Symbol, Money
from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
from infrastructure.brokers.adapters.binance_adapter import BinanceBrokerAdapter
from infrastructure.brokers.adapters.mexc_adapter import MEXCBrokerAdapter
from infrastructure.brokers.adapters.phemex_adapter import PhemexBrokerAdapter


@pytest.mark.unit
def test_bingx_adapter_position_side_robustness(monkeypatch):
    b = object.__new__(_BingXBroker)
    b.logger = logging.getLogger("test_bingx_side")
    
    sent_payloads = []
    monkeypatch.setattr(b, "_make_request",
                        lambda method, endpoint, params=None, data=None, signed=False:
                        (sent_payloads.append(data), {"code": 0, "data": {"order": {"orderId": "BINGX1"}}})[1])

    # 1. Test with OrderSide.BUY enum
    order_enum_buy = Order(
        symbol=Symbol("BTCUSDT"),
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        order_type="MARKET"
    )
    b.execute_order(order_enum_buy)
    assert sent_payloads[-1].get("side") == "BUY"
    assert sent_payloads[-1].get("positionSide") == "LONG"

    # 2. Test with string "BUY"
    order_str_buy = Order(
        symbol=Symbol("BTCUSDT"),
        side="BUY",  # string type
        quantity=Decimal("0.001"),
        order_type="MARKET"
    )
    b.execute_order(order_str_buy)
    assert sent_payloads[-1].get("side") == "BUY"
    assert sent_payloads[-1].get("positionSide") == "LONG"

    # 3. Test with OrderSide.SELL enum
    order_enum_sell = Order(
        symbol=Symbol("BTCUSDT"),
        side=OrderSide.SELL,
        quantity=Decimal("0.001"),
        order_type="MARKET"
    )
    b.execute_order(order_enum_sell)
    assert sent_payloads[-1].get("side") == "SELL"
    assert sent_payloads[-1].get("positionSide") == "SHORT"

    # 4. Test with string "SELL"
    order_str_sell = Order(
        symbol=Symbol("BTCUSDT"),
        side="SELL",  # string type
        quantity=Decimal("0.001"),
        order_type="MARKET"
    )
    b.execute_order(order_str_sell)
    assert sent_payloads[-1].get("side") == "SELL"
    assert sent_payloads[-1].get("positionSide") == "SHORT"


@pytest.mark.unit
def test_binance_adapter_side_robustness(monkeypatch):
    b = object.__new__(BinanceBrokerAdapter)
    b.connected = True
    
    class MockBinanceClient:
        def place_order(self, **kwargs):
            return {"orderId": 12345, "side": kwargs.get("side")}
            
    b.client = MockBinanceClient()

    # 1. Test with OrderSide.BUY enum
    order_enum_buy = Order(symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("0.001"))
    res_enum_buy = b.place_order(order_enum_buy)
    assert res_enum_buy == "12345"

    # 2. Test with string "BUY"
    order_str_buy = Order(symbol=Symbol("BTCUSDT"), side="BUY", quantity=Decimal("0.001"))
    res_str_buy = b.place_order(order_str_buy)
    assert res_str_buy == "12345"


@pytest.mark.unit
def test_mexc_adapter_side_robustness(monkeypatch):
    b = object.__new__(MEXCBrokerAdapter)
    b.connected = True
    
    sent_params = {}
    
    def mock_make_request(method, path, params=None, body="", signed=False):
        # parse body
        pairs = body.split("&")
        for p in pairs:
            k, v = p.split("=")
            sent_params[k] = v
        return {"orderId": "MEXC123"}
        
    monkeypatch.setattr(b, "_make_request", mock_make_request)

    # 1. Test with OrderSide.BUY enum
    order_enum_buy = Order(symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("0.001"))
    b.place_order(order_enum_buy)
    assert sent_params.get("side") == "BUY"

    # 2. Test with string "BUY"
    order_str_buy = Order(symbol=Symbol("BTCUSDT"), side="BUY", quantity=Decimal("0.001"))
    b.place_order(order_str_buy)
    assert sent_params.get("side") == "BUY"


@pytest.mark.unit
def test_phemex_adapter_side_robustness(monkeypatch):
    b = object.__new__(PhemexBrokerAdapter)
    b.connected = True
    
    sent_params = {}
    monkeypatch.setattr(b, "_make_request",
                        lambda method, path, params=None, signed=False:
                        (sent_params.update(params), {"orderId": "PHEMEX123"})[1])

    # 1. Test with OrderSide.BUY enum
    order_enum_buy = Order(symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("0.001"))
    b.place_order(order_enum_buy)
    assert sent_params.get("side") == "Buy"

    # 2. Test with string "BUY"
    order_str_buy = Order(symbol=Symbol("BTCUSDT"), side="BUY", quantity=Decimal("0.001"))
    b.place_order(order_str_buy)
    assert sent_params.get("side") == "Buy"


@pytest.mark.unit
def test_broker_execution_service_side_robustness(monkeypatch):
    from infrastructure.services.broker_execution_service import BrokerExecutionService
    from domain.entities import Order
    from domain.value_objects import Symbol, Money
    from decimal import Decimal
    
    # Mock settings
    class MockConfig:
        pass
    settings = MockConfig()
    settings.execution = MockConfig()
    settings.execution.prevent_same_direction_trade_per_symbol = True
    settings.broker = MockConfig()
    settings.broker.default_broker = "bingx"
    settings.broker.bingx_api_key = "key"
    settings.broker.bingx_secret_key = "secret"
    settings.broker.bingx_passphrase = "pass"
    settings.broker.bingx_testnet = True
    settings.monitoring = MockConfig()
    settings.monitoring.telegram_notifications_enabled = False
    
    # Mock symbol validation so any symbol is approved
    monkeypatch.setattr("infrastructure.services.symbol_validator.symbol_validator.is_symbol_approved", lambda s: True)
    
    # Create execution service instance (skip connect)
    monkeypatch.setattr("infrastructure.brokers.adapters.bingx_adapter.BingXBrokerAdapter.connect", lambda self: None)
    monkeypatch.setattr("infrastructure.brokers.adapters.bingx_adapter.BingXBrokerAdapter.get_position", lambda self, sym: None)
    
    svc = BrokerExecutionService(settings=settings, broker_type="bingx")
    
    # Test order with string "BUY" and string side validation / enhancement
    order_str_buy = Order(
        symbol=Symbol("BTCUSDT"),
        side="BUY",
        quantity=Decimal("0.001"),
        price=Money(Decimal("60000"), "USDT")
    )
    
    # Check that enhancement works without AttributeErrors on string side
    enhanced = svc._enhance_order_with_risk_parameters(order_str_buy)
    assert enhanced is not None
    assert enhanced.stop_loss_price is not None
    assert enhanced.take_profit_price is not None
    
    # Check that pre-broker parameter validation works for string BUY side
    assert svc._validate_order_parameters_before_broker(enhanced) is True


@pytest.mark.unit
def test_multi_broker_execution_service_side_robustness(monkeypatch):
    from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService
    from domain.entities import Order
    from domain.value_objects import Symbol, Money
    from decimal import Decimal
    
    # Mock settings
    class MockConfig:
        pass
    settings = MockConfig()
    settings.execution = MockConfig()
    settings.execution.prevent_same_direction_trade_per_symbol = True
    settings.broker = MockConfig()
    settings.broker.default_broker = "bingx"
    settings.broker.bingx_order_placement_enabled = True
    settings.broker.bingx_api_key = "key"
    settings.broker.bingx_secret_key = "secret"
    settings.broker.bingx_passphrase = "pass"
    settings.broker.bingx_testnet = True
    
    # Mock symbol validation
    monkeypatch.setattr("infrastructure.services.symbol_validator.symbol_validator.is_symbol_approved", lambda s: True)
    
    # Create multi broker service
    svc = MultiBrokerExecutionService(settings=settings)
    
    order_str_buy = Order(
        symbol=Symbol("BTCUSDT"),
        side="BUY",
        quantity=Decimal("0.001"),
        price=Money(Decimal("60000"), "USDT")
    )
    
    # Check that enhancement works without AttributeErrors
    enhanced = svc._enhance_order_with_risk_parameters(order_str_buy)
    assert enhanced is not None
    
    # Check validation
    assert svc._validate_order_parameters_before_broker(enhanced) is True
