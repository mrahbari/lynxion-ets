"""
Use cases for the enterprise hedge fund trading system.

These represent specific business operations that the system performs.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from domain.entities.trading_entities import Signal, Order, Position
from domain.value_objects import Symbol, Money, Percentage
from application.services.trading_services import (
    SignalProcessingService, TradingExecutionService, 
    PortfolioManagementService, RiskManagementService
)


class GenerateTradingSignalUseCase:
    """Use case for generating a trading signal"""
    
    def __init__(self, signal_service: SignalProcessingService):
        self.signal_service = signal_service
    
    def execute(self, symbol: Symbol) -> Optional[Signal]:
        """Execute the use case to generate a trading signal"""
        return self.signal_service.generate_and_process_signal(symbol)


class ExecuteTradingSignalUseCase:
    """Use case for executing a trading signal"""
    
    def __init__(self, trading_service: TradingExecutionService):
        self.trading_service = trading_service
    
    def execute(self, signal: Signal) -> Optional[str]:  # Returns order ID
        """Execute the use case to trade based on a signal"""
        return self.trading_service.execute_signal(signal)


class RebalancePortfolioUseCase:
    """Use case for rebalancing the portfolio"""
    
    def __init__(self, portfolio_service: PortfolioManagementService):
        self.portfolio_service = portfolio_service
    
    def execute(self, target_allocations: Dict[Symbol, Percentage]) -> List[Order]:
        """Execute the use case to rebalance portfolio"""
        return self.portfolio_service.rebalance_portfolio(target_allocations)


class ValidateRiskUseCase:
    """Use case for validating risk parameters"""
    
    def __init__(self, risk_service: RiskManagementService):
        self.risk_service = risk_service
    
    def execute(self, signal: Signal) -> bool:
        """Execute the use case to validate if a trade is allowed"""
        return self.risk_service.validate_trade(signal)
    
    def check_portfolio_status(self) -> Dict[str, Any]:
        """Check the overall portfolio risk status"""
        return self.risk_service.check_portfolio_risk()


class GetPositionUseCase:
    """Use case for retrieving position information"""
    
    def __init__(self, position_service):
        self.position_service = position_service
    
    def execute(self, symbol: Symbol) -> Optional[Position]:
        """Execute the use case to get position for a symbol"""
        return self.position_service.get_position(symbol)
    
    def get_all_positions(self) -> List[Position]:
        """Execute the use case to get all positions"""
        return self.position_service.get_all_positions()


class ProcessMultipleSignalsUseCase:
    """Use case for processing and fusing multiple signals"""
    
    def __init__(self, signal_service: SignalProcessingService):
        self.signal_service = signal_service
    
    def execute(self, signals: List[Signal]) -> Optional[Signal]:
        """Execute the use case to process multiple signals"""
        if not signals:
            return None
        return self.signal_service.process_multiple_signals(signals)


class GetMarketDataUseCase:
    """Use case for retrieving market data"""
    
    def __init__(self, market_data_service):
        self.market_data_service = market_data_service
    
    def get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get the current price for a symbol"""
        return self.market_data_service.get_price(symbol)
    
    def get_historical_data(self, symbol: Symbol, period: str) -> List[float]:
        """Get historical prices for a symbol"""
        return self.market_data_service.get_historical_prices(symbol, period)


class CalculatePnLUseCase:
    """Use case for calculating profit and loss"""
    
    def __init__(self, position_service, market_data_service):
        self.position_service = position_service
        self.market_data_service = market_data_service
    
    def execute(self, position: Position) -> Money:
        """Calculate P&L for a specific position"""
        current_price = self.market_data_service.get_price(position.symbol)
        if not current_price:
            # Return the stored unrealized P&L or 0 if not available
            return position.unrealized_pnl or Money(0, position.entry_price.currency)
        
        return self.position_service.calculate_pnl(position, current_price)