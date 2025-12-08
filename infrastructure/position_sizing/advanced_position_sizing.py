"""
Advanced position sizing models for enterprise hedge fund trading.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
import numpy as np

from domain.entities.trading_entities import Signal
from domain.value_objects import Money, Percentage


class PositionSizingModel(ABC):
    """Abstract base class for position sizing models"""
    
    @abstractmethod
    def calculate_size(self, 
                      entry_price: Money, 
                      stop_loss: Money, 
                      portfolio_equity: float,
                      risk_percentage: Percentage, 
                      market_data: dict = None) -> Decimal:
        """Calculate position size based on the model"""
        pass


class FixedRiskPositionSizingModel(PositionSizingModel):
    """Fixed risk percentage position sizing"""
    
    def calculate_size(self, 
                      entry_price: Money, 
                      stop_loss: Money, 
                      portfolio_equity: float,
                      risk_percentage: Percentage, 
                      market_data: dict = None) -> Decimal:
        """Calculate position size based on fixed risk percentage"""
        risk_amount = portfolio_equity * float(risk_percentage.value)
        risk_per_unit = abs(float(entry_price.amount) - float(stop_loss.amount))
        
        if risk_per_unit <= 0:
            # Use a default risk distance if stop loss is not provided or invalid
            risk_per_unit = float(entry_price.amount) * 0.02  # 2% default risk distance
        
        size = risk_amount / risk_per_unit
        return Decimal(int(size))  # Return as integer number of units


class KellyPositionSizingModel(PositionSizingModel):
    """Position sizing based on Kelly Criterion"""
    
    def __init__(self, max_kelly_fraction: float = 0.25):  # Use 25% of Kelly to reduce risk
        self.max_kelly_fraction = max_kelly_fraction
    
    def calculate_size(self, 
                      entry_price: Money, 
                      stop_loss: Money, 
                      portfolio_equity: float,
                      risk_percentage: Percentage, 
                      market_data: dict = None) -> Decimal:
        """Calculate position size using Kelly Criterion"""
        if market_data is None:
            # Use a default Kelly calculation with assumed win rate and payoff ratio
            win_rate = 0.55  # 55% win rate
            avg_win = 0.10   # 10% average win
            avg_loss = 0.05  # 5% average loss
        else:
            win_rate = market_data.get('win_rate', 0.55)
            avg_win = market_data.get('avg_win', 0.10)
            avg_loss = market_data.get('avg_loss', 0.05)
        
        # Kelly formula: K = (bp - q) / b
        # b = net odds (avg_win / avg_loss)
        # p = probability of win
        # q = probability of loss (1 - p)
        b = avg_win / (avg_loss + 1e-8)
        p = win_rate
        q = 1 - p
        
        kelly_fraction = (b * p - q) / (b + 1e-8)
        # Apply safety factor to reduce actual Kelly position size
        effective_fraction = min(kelly_fraction * self.max_kelly_fraction, 0.25)  # Cap at 25%
        effective_fraction = max(effective_fraction, 0)  # Ensure positive
        
        size = portfolio_equity * effective_fraction / float(entry_price.amount)
        return Decimal(int(size))


class ATRPositionSizingModel(PositionSizingModel):
    """Position sizing based on Average True Range (ATR)"""
    
    def calculate_size(self, 
                      entry_price: Money, 
                      stop_loss: Money, 
                      portfolio_equity: float,
                      risk_percentage: Percentage, 
                      market_data: dict = None) -> Decimal:
        """Calculate position size based on ATR risk"""
        if market_data is None or 'atr' not in market_data:
            # If no ATR data, use the stop loss distance as proxy
            atr = abs(float(entry_price.amount) - float(stop_loss.amount))
        else:
            atr = market_data['atr']
        
        risk_amount = portfolio_equity * float(risk_percentage.value)
        size = risk_amount / (atr + 1e-8)
        return Decimal(int(size))


class VolatilityBasedSizingModel(PositionSizingModel):
    """Position sizing based on volatility percentage"""
    
    def calculate_size(self, 
                      entry_price: Money, 
                      stop_loss: Money, 
                      portfolio_equity: float,
                      risk_percentage: Percentage, 
                      market_data: dict = None) -> Decimal:
        """Calculate position size inversely proportional to volatility"""
        if market_data is None or 'volatility' not in market_data:
            # Default to 20% annualized volatility if not provided
            volatility = 0.20
        else:
            volatility = market_data['volatility']
        
        # Scale position size inversely to volatility
        volatility_factor = 1.0 / (volatility + 0.1)  # Add 0.1 to prevent high leverage with low volatility
        base_size = (portfolio_equity * float(risk_percentage.value)) / (abs(float(entry_price.amount) - float(stop_loss.amount)) + 1e-8)
        size = base_size * volatility_factor
        return Decimal(int(size))


class PositionSizingService:
    """Service to manage different position sizing models"""
    
    def __init__(self, portfolio_equity: float, risk_per_trade: float = 0.01):
        self.portfolio_equity = portfolio_equity
        self.risk_per_trade = risk_per_trade
        
        self.models = {
            'fixed_risk': FixedRiskPositionSizingModel(),
            'kelly': KellyPositionSizingModel(),
            'atr': ATRPositionSizingModel(),
            'volatility': VolatilityBasedSizingModel()
        }
    
    def calculate_position_size(self, 
                               signal: Signal, 
                               sizing_model: str = 'fixed_risk',
                               market_data: dict = None) -> Decimal:
        """Calculate position size using specified model"""
        if sizing_model not in self.models:
            raise ValueError(f"Unknown sizing model: {sizing_model}")
        
        model = self.models[sizing_model]
        
        return model.calculate_size(
            entry_price=signal.price,
            stop_loss=signal.stop_loss if signal.stop_loss else Money(signal.price.amount * Decimal('0.98'), signal.price.currency),  # Default 2% stop loss
            portfolio_equity=self.portfolio_equity,
            risk_percentage=Percentage(self.risk_per_trade),
            market_data=market_data
        )
    
    def calculate_optimal_size(self, signal: Signal, market_data: dict = None) -> Decimal:
        """Calculate optimal size using ensemble of models"""
        sizes = []
        for model_name, model in self.models.items():
            try:
                size = model.calculate_size(
                    entry_price=signal.price,
                    stop_loss=signal.stop_loss if signal.stop_loss else Money(signal.price.amount * Decimal('0.98'), signal.price.currency),
                    portfolio_equity=self.portfolio_equity,
                    risk_percentage=Percentage(self.risk_per_trade),
                    market_data=market_data
                )
                sizes.append(float(size))
            except:
                continue  # Skip if model fails
        
        if sizes:
            # Take the median size as a robust estimate
            median_size = np.median(sizes)
            return Decimal(str(int(median_size)))
        else:
            # Fallback to fixed risk model
            return self.calculate_position_size(signal, 'fixed_risk', market_data)