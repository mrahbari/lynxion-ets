"""
Unit tests for domain layer components in the enterprise hedge fund trading system.
"""
import unittest
from decimal import Decimal
from datetime import datetime
from domain.value_objects import Symbol, Money, Percentage
from domain.entities.trading_entities import Signal, Order, Position, SignalType, OrderSide, PositionSide


class TestSymbol(unittest.TestCase):
    """Test Symbol value object"""
    
    def test_create_valid_symbol(self):
        """Test creating a valid symbol"""
        symbol = Symbol("BTCUSDT")
        self.assertEqual(symbol.value, "BTCUSDT")
        self.assertEqual(symbol.base_asset(), "BTC")
        self.assertEqual(symbol.quote_asset(), "USDT")
    
    def test_invalid_symbol_format_raises_error(self):
        """Test that invalid symbol formats raise an error"""
        with self.assertRaises(ValueError):
            Symbol("INVALID_FORMAT")


class TestMoney(unittest.TestCase):
    """Test Money value object"""
    
    def test_create_money(self):
        """Test creating a Money value object"""
        money = Money(Decimal("1000.50"), "USDT")
        self.assertEqual(money.amount, Decimal("1000.50"))
        self.assertEqual(money.currency, "USDT")
    
    def test_money_operations(self):
        """Test money operations"""
        money1 = Money(Decimal("1000"), "USDT")
        money2 = Money(Decimal("500"), "USDT")
        
        result = money1 + money2
        self.assertEqual(result.amount, Decimal("1500"))
        
        result = money1 - money2
        self.assertEqual(result.amount, Decimal("500"))


class TestPercentage(unittest.TestCase):
    """Test Percentage value object"""
    
    def test_create_percentage(self):
        """Test creating a Percentage value object"""
        percentage = Percentage(Decimal("0.75"))
        self.assertEqual(percentage.value, Decimal("0.75"))
        self.assertAlmostEqual(float(percentage.value), 0.75, places=2)
    
    def test_percentage_validation(self):
        """Test that percentages are within valid range"""
        with self.assertRaises(ValueError):
            Percentage(Decimal("1.5"))  # Greater than 1.0
        
        with self.assertRaises(ValueError):
            Percentage(Decimal("-0.1"))  # Negative


class TestSignal(unittest.TestCase):
    """Test Signal entity"""
    
    def test_create_signal(self):
        """Test creating a signal entity"""
        symbol = Symbol("BTCUSDT")
        confidence = Percentage(Decimal("0.75"))
        
        signal = Signal(
            symbol=symbol,
            signal_type=SignalType.BUY,
            confidence=confidence,
            score=0.6,
            strategy_name="TestStrategy",
            timestamp=datetime.now()
        )
        
        self.assertEqual(signal.symbol.value, "BTCUSDT")
        self.assertEqual(signal.signal_type.name, "BUY")
        self.assertEqual(float(signal.confidence.value), 0.75)
        self.assertEqual(signal.score, 0.6)
        self.assertEqual(signal.strategy_name, "TestStrategy")
    
    def test_signal_post_init_validation(self):
        """Test post-init validation of signal"""
        symbol = Symbol("BTCUSDT")
        confidence = Percentage(Decimal("0.75"))
        
        # Test that score must be within valid range
        with self.assertRaises(ValueError):
            Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                score=1.5,  # Invalid score
                strategy_name="TestStrategy",
                timestamp=datetime.now()
            )


class TestOrder(unittest.TestCase):
    """Test Order entity"""
    
    def test_create_order(self):
        """Test creating an order entity"""
        symbol = Symbol("BTCUSDT")
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=Decimal("0.5"),
            order_type="MARKET",
            timestamp=datetime.now()
        )
        
        self.assertEqual(order.symbol.value, "BTCUSDT")
        self.assertEqual(order.side.name, "BUY")
        self.assertEqual(order.quantity, Decimal("0.5"))


class TestPosition(unittest.TestCase):
    """Test Position entity"""
    
    def test_create_position(self):
        """Test creating a position entity"""
        symbol = Symbol("BTCUSDT")
        money = Money(Decimal("45000"), "USDT")
        
        position = Position(
            symbol=symbol,
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=money,
            timestamp=datetime.now()
        )
        
        self.assertEqual(position.symbol.value, "BTCUSDT")
        self.assertEqual(position.side.name, "LONG")
        self.assertEqual(position.quantity, Decimal("0.5"))
        self.assertEqual(position.entry_price.amount, Decimal("45000"))


if __name__ == '__main__':
    unittest.main()