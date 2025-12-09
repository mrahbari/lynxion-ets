from typing import Dict, List, Optional
from domain.entities.trading_entities import Signal, Order, Position
from domain.value_objects import Symbol, Money
from domain.ports.engine_ports import StrategyPort, EnginePort, FusionPort
from domain.ports.trading_ports import (
    SignalPort, OrderManagementPort, MarketDataPort, 
    PositionManagementPort, RiskManagementPort
)
from application.containers.container import container


class SignalFactory:
    """Factory for creating and managing trading signals"""
    
    @staticmethod
    def create_signal(symbol: Symbol, signal_type: str, confidence: float, score: float, 
                     strategy_name: str, source_engine: Optional[str] = None, 
                     metadata: Optional[Dict] = None) -> Signal:
        from domain.entities.trading_entities import SignalType
        from domain.value_objects import Percentage
        from datetime import datetime
        
        signal_type_enum = SignalType[signal_type.upper()]
        confidence_pct = Percentage(min(max(confidence, 0.0), 1.0))  # Clamp between 0 and 1
        
        return Signal(
            symbol=symbol,
            signal_type=signal_type_enum,
            confidence=confidence_pct,
            score=max(min(score, 1.0), -1.0),  # Clamp between -1 and 1
            strategy_name=strategy_name,
            timestamp=datetime.now(),
            source_engine=source_engine,
            metadata=metadata or {}
        )


class OrderFactory:
    """Factory for creating trading orders"""
    
    @staticmethod
    def create_order(symbol: Symbol, side: str, quantity: float, 
                    order_type: str = "MARKET", price: Optional[float] = None,
                    parent_signal: Optional[Signal] = None) -> Order:
        from domain.entities.trading_entities import OrderSide
        from domain.value_objects import Money
        from datetime import datetime
        from decimal import Decimal
        
        side_enum = OrderSide[side.upper()]
        price_money = Money(Decimal(str(price)), symbol.quote_asset()) if price else None
        
        return Order(
            symbol=symbol,
            side=side_enum,
            quantity=Decimal(str(quantity)),
            price=price_money,
            order_type=order_type.upper(),
            timestamp=datetime.now(),
            parent_signal=parent_signal
        )


class PositionFactory:
    """Factory for creating trading positions"""
    
    @staticmethod
    def create_position(symbol: Symbol, side: str, quantity: float, 
                       entry_price: float, strategy_name: Optional[str] = None) -> Position:
        from domain.entities.trading_entities import PositionSide
        from domain.value_objects import Money
        from datetime import datetime
        from decimal import Decimal
        
        side_enum = PositionSide[side.upper()]
        entry_price_money = Money(Decimal(str(entry_price)), symbol.quote_asset())
        
        return Position(
            symbol=symbol,
            side=side_enum,
            quantity=Decimal(str(quantity)),
            entry_price=entry_price_money,
            timestamp=datetime.now(),
            strategy_name=strategy_name
        )


class TradingServiceFactory:
    """Factory for creating trading services with proper dependencies"""
    
    @staticmethod
    def create_signal_service() -> SignalPort:
        from infrastructure.services.signal_service import SignalProcessingService
        return SignalProcessingService(
            engine_port=container.resolve('engine_service'),
            strategy_port=container.resolve('strategy_service')
        )
    
    @staticmethod
    def create_order_service() -> OrderManagementPort:
        from infrastructure.services.order_service import OrderManagementService
        return OrderManagementService(
            broker_port=container.resolve('broker_service'),
            risk_port=container.resolve('risk_service')
        )
    
    @staticmethod
    def create_market_data_service() -> MarketDataPort:
        from infrastructure.services.market_data_service import MarketDataService
        return MarketDataService(
            data_port=container.resolve('data_service')
        )
    
    @staticmethod
    def create_position_service() -> PositionManagementPort:
        from infrastructure.services.position_service import PositionManagementService
        return PositionManagementService(
            broker_port=container.resolve('broker_service')
        )
    
    @staticmethod
    def create_risk_service() -> RiskManagementPort:
        from infrastructure.services.risk_service import RiskManagementService
        return RiskManagementService(
            risk_governor_port=container.resolve('risk_governor_service'),
            position_port=container.resolve('position_service')
        )