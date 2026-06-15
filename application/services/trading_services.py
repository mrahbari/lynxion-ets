"""
Application services for the enterprise hedge fund trading system.

These services orchestrate domain objects and coordinate between different ports.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Signal, Order, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.trading_ports import (
    SignalPort, OrderManagementPort, MarketDataPort, 
    PositionManagementPort, RiskManagementPort
)
from domain.ports.engine_ports import (
    EnginePort, StrategyPort, FusionPort, RiskGovernorPort
)
from datetime import datetime


class SignalProcessingService:
    """Application service for signal processing and orchestration"""
    
    def __init__(self, signal_port: SignalPort, engine_port: EnginePort, fusion_port: FusionPort):
        self.signal_port = signal_port
        self.engine_port = engine_port
        self.fusion_port = fusion_port
    
    def generate_and_process_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal and process it through engines and fusion"""
        # Generate initial signal
        raw_signal = self.signal_port.generate_signal(symbol)
        if not raw_signal:
            return None
        
        # Process through engine
        processed_signal = self.engine_port.process_signal(raw_signal)
        
        # Return the processed signal
        return processed_signal
    
    def process_multiple_signals(self, signals: List[Signal]) -> Signal:
        """Fuse multiple signals into a single signal"""
        if not signals:
            return None
        
        # Fuse the signals
        fused_signal = self.fusion_port.fuse_signals(signals)
        return fused_signal


class TradingExecutionService:
    """Application service for executing trades"""
    
    def __init__(self, 
                 order_management_port: OrderManagementPort,
                 position_management_port: PositionManagementPort,
                 risk_management_port: RiskManagementPort,
                 market_data_port: MarketDataPort):
        self.order_management = order_management_port
        self.position_management = position_management_port
        self.risk_management = risk_management_port
        self.market_data = market_data_port
    
    def execute_signal(self, signal: Signal) -> Optional[str]:
        """Execute a trading signal by placing appropriate orders"""
        # Check risk limits before executing
        if not self.risk_management.validate_order_risk(
            self._create_test_order(signal)
        ):
            return None  # Risk validation failed
        
        # Get current market data
        current_price = self.market_data.get_price(signal.symbol)
        if not current_price:
            return None
        
        # Calculate position size based on signal and risk parameters
        position_size = self._calculate_position_size(signal, current_price)
        if position_size <= 0:
            return None
        
        # Create order based on signal
        order = self._create_order_from_signal(signal, position_size, current_price)
        
        # Place the order
        order_id = self.order_management.place_order(order)
        return order_id
    
    def _create_test_order(self, signal: Signal) -> Order:
        """Create a test order for risk validation"""
        from application.factories.trading_factories import OrderFactory
        return OrderFactory.create_order(
            symbol=signal.symbol,
            side="BUY" if signal.signal_type.name == "BUY" else "SELL",
            quantity=1.0,  # Test quantity
            order_type="MARKET"
        )
    
    def _calculate_position_size(self, signal: Signal, current_price: float) -> float:
        """Calculate appropriate position size based on signal and risk"""
        # This would integrate with risk management and portfolio allocation logic
        # For now, returning a basic calculation
        account_value = self._get_account_value()
        risk_percentage = float(signal.confidence) * 0.02  # Risk up to 2% based on confidence
        max_risk_amount = account_value * risk_percentage
        position_size = max_risk_amount / current_price
        return min(position_size, account_value * 0.1)  # Cap at 10% of account
    
    def _create_order_from_signal(self, signal: Signal, size: float, price: float) -> Order:
        """Create an order from a trading signal"""
        from application.factories.trading_factories import OrderFactory
        side = "BUY" if signal.signal_type.name == "BUY" else "SELL"
        return OrderFactory.create_order(
            symbol=signal.symbol,
            side=side,
            quantity=size,
            price=price if signal.signal_type.name == "LIMIT" else None,
            order_type="MARKET"  # Default to market order
        )
    
    def _get_account_value(self) -> float:
        """Get the current account value"""
        # This would integrate with the broker/portfolio service
        # For now, return a placeholder
        return 100000.0  # $100,000 default


class PortfolioManagementService:
    """Application service for portfolio management"""
    
    def __init__(self, 
                 position_management_port: PositionManagementPort,
                 market_data_port: MarketDataPort,
                 risk_management_port: RiskManagementPort):
        self.position_management = position_management_port
        self.market_data = market_data_port
        self.risk_management = risk_management_port
    
    def get_portfolio_exposure(self) -> Money:
        """Get total portfolio exposure"""
        return self.risk_management.get_portfolio_exposure()
    
    def rebalance_portfolio(self, target_allocations: Dict[Symbol, Percentage]) -> List[Order]:
        """Generate rebalancing orders based on target allocations"""
        current_positions = self.position_management.get_all_positions()
        orders = []
        
        for symbol, target_pct in target_allocations.items():
            # Calculate current allocation
            current_position = self.position_management.get_position(symbol)
            
            # Get current market price
            current_price = self.market_data.get_price(symbol)
            if not current_price:
                continue
            
            # Based on the difference between target and current allocation,
            # create orders to rebalance
            # This is a simplified implementation - real implementation would be more complex
            orders.extend(self._generate_rebalance_orders(
                symbol, current_position, target_pct, current_price
            ))
        
        return orders
    
    def _generate_rebalance_orders(self, symbol: Symbol, current_position: Optional[Position], 
                                  target_pct: Percentage, current_price: float) -> List[Order]:
        """Generate orders to rebalance to target allocation"""
        # Implementation would calculate the difference between current and target allocation
        # and create orders to adjust positions accordingly
        return []


class RiskManagementService:
    """Application service for risk management"""
    
    def __init__(self, risk_governor_port: RiskGovernorPort):
        self.risk_governor = risk_governor_port
    
    def validate_trade(self, signal: Signal) -> bool:
        """Validate if a trade is allowed based on risk parameters"""
        return self.risk_governor.validate_signal(signal)
    
    def check_portfolio_risk(self) -> Dict[str, Any]:
        """Check overall portfolio risk status"""
        risk_status = {
            'drawdown_limit_ok': self.risk_governor.check_drawdown_limits(),
            'correlation_limits_ok': True,  # This would check actual correlation
            'max_position_size_ok': True,   # This would check actual position sizes
        }
        return risk_status