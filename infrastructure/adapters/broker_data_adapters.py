"""
Infrastructure adapters for broker integrations.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Order, Position
from domain.value_objects import Symbol, Money
from abc import ABC, abstractmethod
import time


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters"""
    
    @abstractmethod
    def place_order(self, order: Order) -> str:
        """Place an order on the broker"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        """Cancel an order on the broker"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        """Get the status of an order"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get position for a symbol"""
        pass
    
    @abstractmethod
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        pass


class MockBrokerAdapter(BrokerAdapter):
    """Mock broker adapter for testing and development"""
    
    def __init__(self):
        self.orders = {}
        self.positions = {}
        self.order_id_counter = 1000
    
    def place_order(self, order: Order) -> str:
        """Place an order on the mock broker"""
        order_id = f"MOCK_ORDER_{self.order_id_counter}"
        self.order_id_counter += 1
        self.orders[order_id] = {
            'order': order,
            'status': 'NEW',
            'timestamp': time.time()
        }
        return order_id
    
    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        """Cancel an order on the mock broker"""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'CANCELED'
            return True
        return False
    
    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        """Get the status of an order"""
        if order_id in self.orders:
            return self.orders[order_id]['status']
        return 'NOT_FOUND'
    
    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get position for a symbol"""
        # Return a mock position
        from domain.entities import PositionSide
        from domain.value_objects import Money
        from decimal import Decimal
        from datetime import datetime
        
        if symbol.value in self.positions:
            return self.positions[symbol.value]
        
        # Create a default position (flat)
        return Position(
            symbol=symbol,
            side=PositionSide.FLAT,
            quantity=Decimal('0'),
            entry_price=Money(0, symbol.quote_asset()),
            timestamp=datetime.now()
        )
    
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        # Return mock positions
        from domain.entities import PositionSide
        from domain.value_objects import Money
        from decimal import Decimal
        from datetime import datetime
        
        # For demo purposes, return a few mock positions
        btc_symbol = Symbol("BTCUSDT")
        eth_symbol = Symbol("ETHUSDT")
        
        positions = [
            Position(
                symbol=btc_symbol,
                side=PositionSide.LONG,
                quantity=Decimal('0.5'),
                entry_price=Money(45000, "USDT"),
                timestamp=datetime.now()
            ),
            Position(
                symbol=eth_symbol,
                side=PositionSide.SHORT,
                quantity=Decimal('2.0'),
                entry_price=Money(2500, "USDT"),
                timestamp=datetime.now()
            )
        ]
        
        return positions


class DataAdapter(ABC):
    """Abstract base class for data adapters"""
    
    @abstractmethod
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for symbol"""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: Symbol, period: str) -> List[float]:
        """Get historical prices for symbol"""
        pass
    
    @abstractmethod
    def subscribe_to_market_data(self, symbol: Symbol, callback):
        """Subscribe to real-time market data"""
        pass


class MockDataAdapter(DataAdapter):
    """Mock data adapter for testing and development"""
    
    def __init__(self):
        # Mock price data for demonstration
        self.mock_prices = {
            "BTCUSDT": 45123.45,
            "ETHUSDT": 2567.89,
            "BNBUSDT": 312.56,
        }
        
        # Mock historical data (simple mock for demonstration)
        self.mock_historical = {
            "BTCUSDT": [45000 + i*10 for i in range(100)],  # Increasing prices
            "ETHUSDT": [2500 + i*5 for i in range(100)],     # Increasing prices
        }
    
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for symbol"""
        return self.mock_prices.get(symbol.value, 0.0)
    
    def get_historical_data(self, symbol: Symbol, period: str) -> List[float]:
        """Get historical prices for symbol"""
        # In a real implementation, this would fetch actual historical data
        # based on the requested period
        return self.mock_historical.get(symbol.value, [])
    
    def subscribe_to_market_data(self, symbol: Symbol, callback):
        """Subscribe to real-time market data"""
        # In a real implementation, this would establish a WebSocket connection
        # For mock, we'll just call the callback with mock data periodically
        import threading
        import time
        
        def mock_data_feed():
            while True:
                price = self.get_current_price(symbol)
                callback({
                    'symbol': symbol.value,
                    'price': price,
                    'timestamp': time.time()
                })
                time.sleep(5)  # Update every 5 seconds for demo
        
        # Start the mock data feed in a separate thread
        thread = threading.Thread(target=mock_data_feed, daemon=True)
        thread.start()