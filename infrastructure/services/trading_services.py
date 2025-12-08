from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import Signal, Order, Fill, Position
from domain.value_objects import Symbol, Money
from domain.ports.trading_ports import (
    SignalPort, OrderManagementPort, MarketDataPort, 
    PositionManagementPort, RiskManagementPort
)
from shared.logger import logger
from datetime import datetime


class SignalProcessingService(SignalPort):
    """Infrastructure implementation of SignalPort"""
    
    def __init__(self, engine_port, strategy_port):
        self.engine_port = engine_port
        self.strategy_port = strategy_port
    
    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal from strategies"""
        # This would call the strategy port to generate signals
        # For now, returning a placeholder
        logger.info(f"Generating signal for symbol: {symbol.value}")
        return None
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through engines"""
        # Process the signal through the engine
        processed_signal = self.engine_port.process_signal(signal)
        logger.info(f"Processed signal for {signal.symbol.value} with confidence {signal.confidence}")
        return processed_signal


class OrderManagementService(OrderManagementPort):
    """Infrastructure implementation of OrderManagementPort"""
    
    def __init__(self, broker_port, risk_port):
        self.broker_port = broker_port
        self.risk_port = risk_port
    
    def place_order(self, order: Order) -> str:
        """Place an order through the broker"""
        # Validate risk before placing order
        if not self.risk_port.validate_order_risk(order):
            raise Exception("Order failed risk validation")
        
        # Place order through broker port
        order_id = self.broker_port.place_order(order)
        logger.info(f"Order placed: {order_id} for {order.symbol.value}")
        return order_id
    
    def cancel_order(self, order_id: str, symbol: Symbol) -> bool:
        """Cancel an order through the broker"""
        success = self.broker_port.cancel_order(order_id, symbol)
        logger.info(f"Order cancellation: {order_id}, Success: {success}")
        return success
    
    def get_order_status(self, order_id: str, symbol: Symbol) -> str:
        """Get order status from broker"""
        status = self.broker_port.get_order_status(order_id, symbol)
        logger.info(f"Order status: {order_id} = {status}")
        return status


class MarketDataService(MarketDataPort):
    """Infrastructure implementation of MarketDataPort"""
    
    def __init__(self, data_port):
        self.data_port = data_port
    
    def get_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for symbol"""
        price = self.data_port.get_current_price(symbol)
        logger.info(f"Price for {symbol.value}: {price}")
        return price
    
    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """Get historical data for symbol"""
        data = self.data_port.get_historical_data(symbol, period, timeframe)
        logger.info(f"Retrieved {len(data)} historical data points for {symbol.value}")
        return data
    
    def subscribe_to_market_data(self, symbol: Symbol, callback):
        """Subscribe to real-time market data"""
        logger.info(f"Subscribing to market data for {symbol.value}")
        self.data_port.subscribe_to_market_data(symbol, callback)


class PositionManagementService(PositionManagementPort):
    """Infrastructure implementation of PositionManagementPort"""
    
    def __init__(self, broker_port):
        self.broker_port = broker_port
    
    def get_position(self, symbol: Symbol) -> Optional[Position]:
        """Get current position for symbol"""
        position = self.broker_port.get_position(symbol)
        logger.info(f"Position for {symbol.value}: {position}")
        return position
    
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        positions = self.broker_port.get_all_positions()
        logger.info(f"Retrieved {len(positions)} positions")
        return positions
    
    def calculate_pnl(self, position: Position, current_price: float) -> Money:
        """Calculate P&L for position"""
        # Calculate P&L based on current price
        pnl = (current_price - float(position.entry_price.amount)) * float(position.quantity)
        if position.side.name == 'SHORT':
            pnl = -pnl
        
        pnl_money = Money(abs(pnl), position.entry_price.currency)
        logger.info(f"P&L calculated for {position.symbol.value}: {pnl_money}")
        return pnl_money


class RiskManagementService(RiskManagementPort):
    """Infrastructure implementation of RiskManagementPort"""
    
    def __init__(self, risk_governor_port, position_port):
        self.risk_governor_port = risk_governor_port
        self.position_port = position_port
    
    def validate_order_risk(self, order: Order) -> bool:
        """Validate if order passes risk checks"""
        is_valid = self.risk_governor_port.validate_order(order)
        logger.info(f"Order risk validation for {order.symbol.value}: {is_valid}")
        return is_valid
    
    def check_portfolio_risk(self) -> bool:
        """Check if portfolio is within risk limits"""
        is_within_limits = self.risk_governor_port.check_portfolio_risk()
        logger.info(f"Portfolio risk check: {is_within_limits}")
        return is_within_limits
    
    def get_portfolio_exposure(self) -> Money:
        """Get total portfolio exposure"""
        exposure = self.risk_governor_port.get_portfolio_exposure()
        logger.info(f"Portfolio exposure: {exposure}")
        return exposure
    
    def is_risk_limit_exceeded(self) -> bool:
        """Check if any risk limits are exceeded"""
        limits_exceeded = self.risk_governor_port.is_risk_limit_exceeded()
        logger.info(f"Risk limits exceeded: {limits_exceeded}")
        return limits_exceeded