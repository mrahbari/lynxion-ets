"""
Advanced Position Sizing Models based on Enterprise Hedge Fund Architecture
"""
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class PositionSizingModel(ABC):
    """
    Abstract base class for position sizing models
    """
    @abstractmethod
    def compute_size(self, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float,
                     volatility: Optional[float] = None,
                     signal_expectancy: Optional[float] = None,
                     regime_accuracy: Optional[float] = None,
                     fusion_confidence: Optional[float] = None,
                     correlation_exposure: Optional[float] = None,
                     current_drawdown: Optional[float] = None,
                     **kwargs) -> float:
        """
        Calculate position size based on the model's logic
        """
        pass


class FixedRiskPositionSizer(PositionSizingModel):
    """
    Fixed Risk-based Position Sizing
    Size based on risk % of portfolio and stop loss distance
    """
    def compute_size(self, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float,
                     volatility: Optional[float] = None,
                     signal_expectancy: Optional[float] = None,
                     regime_accuracy: Optional[float] = None,
                     fusion_confidence: Optional[float] = None,
                     correlation_exposure: Optional[float] = None,
                     current_drawdown: Optional[float] = None,
                     **kwargs) -> float:
        """
        Calculate position size based on fixed risk percentage of portfolio
        """
        # Start with base risk amount
        risk_amount = portfolio_equity * risk_per_trade

        # Adjust risk based on signal expectancy (higher expectancy = higher risk)
        if signal_expectancy is not None:
            # Scale risk proportionally to expectancy (between 0.5 and 1.5 for -1 to +1 expectancy)
            expectancy_factor = 0.5 + (signal_expectancy + 1.0) / 2.0  # Maps -1:+1 to 0.5:1.5
            risk_amount *= expectancy_factor

        # Adjust risk based on regime accuracy (higher accuracy = higher risk)
        if regime_accuracy is not None:
            risk_amount *= regime_accuracy

        # Adjust risk based on fusion confidence (higher confidence = higher risk)
        if fusion_confidence is not None:
            risk_amount *= fusion_confidence

        # Reduce risk based on correlation exposure (higher correlation = lower risk)
        if correlation_exposure is not None:
            correlation_penalty = max(0.1, 1.0 - correlation_exposure)  # At least 10% of original risk
            risk_amount *= correlation_penalty

        # Reduce risk based on current drawdown (higher drawdown = lower risk)
        if current_drawdown is not None:
            drawdown_factor = max(0.1, 1.0 - current_drawdown)  # At least 10% of original risk
            risk_amount *= drawdown_factor

        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            return 1.0  # Default minimum size for invalid stop loss

        # Calculate base size
        size = risk_amount / risk_per_unit

        # Apply additional constraints to prevent unrealistic positions in low-priced assets
        max_size_by_price = portfolio_equity / entry_price if entry_price > 0 else 1.0
        size = min(size, max_size_by_price * 0.1)  # Max 10% of portfolio by value

        # Apply reasonable maximum based on asset price to prevent huge positions in low-priced assets
        if entry_price > 1000:
            size = min(size, 10)  # For expensive assets like BTC
        elif entry_price > 100:
            size = min(size, 100)  # For mid-range assets like ETH
        elif entry_price > 10:
            size = min(size, 1000)  # For low-mid range assets
        else:
            size = min(size, 10000)  # For very low-priced assets like XRP, SHIB

        return max(size, 1.0)  # At least 1 unit


class KellyPositionSizer(PositionSizingModel):
    """
    Kelly Criterion-based Position Sizing
    Uses win rate and reward-to-risk ratio to determine optimal position size
    """
    def compute_size(self, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float,
                     volatility: Optional[float] = None,
                     signal_expectancy: Optional[float] = None,
                     regime_accuracy: Optional[float] = None,
                     fusion_confidence: Optional[float] = None,
                     correlation_exposure: Optional[float] = None,
                     current_drawdown: Optional[float] = None,
                     win_rate: float = 0.5, avg_win_rate: float = 0.1,
                     avg_loss_rate: float = 0.05, **kwargs) -> float:
        """
        Calculate position size using Kelly Criterion formula:
        K = (bp - q) / b
        b = net odds (win_rate / loss_rate)
        p = probability of win
        q = probability of loss (1 - p)
        """
        # Calculate net odds (win_rate / loss_rate)
        b = avg_win_rate / (avg_loss_rate + 1e-8)  # Add small value to prevent division by zero
        p = win_rate
        q = 1 - p

        # Kelly fraction
        kelly_fraction = (b * p - q) / (b + 1e-8)

        # Clamp between 0 and max allowed fraction to prevent overbetting
        kelly_fraction = max(0, min(kelly_fraction, risk_per_trade * 2))  # Don't exceed 2x normal risk

        # Adjust Kelly fraction based on additional factors
        if signal_expectancy is not None:
            expectancy_factor = 0.5 + (signal_expectancy + 1.0) / 2.0
            kelly_fraction *= expectancy_factor

        if regime_accuracy is not None:
            kelly_fraction *= regime_accuracy

        if fusion_confidence is not None:
            kelly_fraction *= fusion_confidence

        if correlation_exposure is not None:
            correlation_penalty = max(0.1, 1.0 - correlation_exposure)
            kelly_fraction *= correlation_penalty

        if current_drawdown is not None:
            drawdown_factor = max(0.1, 1.0 - current_drawdown)
            kelly_fraction *= drawdown_factor

        # Calculate position size based on Kelly fraction
        size = portfolio_equity * kelly_fraction / abs(entry_price - stop_loss)

        # Apply constraints similar to fixed risk model
        max_size_by_price = portfolio_equity / entry_price if entry_price > 0 else 1.0
        size = min(size, max_size_by_price * 0.1)

        if entry_price > 1000:
            size = min(size, 10)
        elif entry_price > 100:
            size = min(size, 100)
        elif entry_price > 10:
            size = min(size, 1000)
        else:
            size = min(size, 10000)

        return max(size, 1.0)


class ATRBasedPositionSizer(PositionSizingModel):
    """
    ATR (Average True Range) based Position Sizing
    Uses volatility measure to adjust position size
    """
    def compute_size(self, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float,
                     volatility: Optional[float] = None,
                     signal_expectancy: Optional[float] = None,
                     regime_accuracy: Optional[float] = None,
                     fusion_confidence: Optional[float] = None,
                     correlation_exposure: Optional[float] = None,
                     current_drawdown: Optional[float] = None,
                     **kwargs) -> float:
        """
        Calculate position size based on ATR (volatility proxy)
        If volatility is not provided, use the stop loss distance as a proxy
        """
        # Start with base risk amount
        risk_amount = portfolio_equity * risk_per_trade

        # Adjust risk based on additional factors
        if signal_expectancy is not None:
            expectancy_factor = 0.5 + (signal_expectancy + 1.0) / 2.0
            risk_amount *= expectancy_factor

        if regime_accuracy is not None:
            risk_amount *= regime_accuracy

        if fusion_confidence is not None:
            risk_amount *= fusion_confidence

        if correlation_exposure is not None:
            correlation_penalty = max(0.1, 1.0 - correlation_exposure)
            risk_amount *= correlation_penalty

        if current_drawdown is not None:
            drawdown_factor = max(0.1, 1.0 - current_drawdown)
            risk_amount *= drawdown_factor

        risk_per_unit = volatility if volatility is not None else abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            risk_per_unit = abs(entry_price - stop_loss)  # Fallback to stop loss distance
            if risk_per_unit <= 0:
                return 1.0  # Default minimum size

        # Calculate size based on ATR/volatility
        size = risk_amount / risk_per_unit

        # Apply same constraints as other models
        max_size_by_price = portfolio_equity / entry_price if entry_price > 0 else 1.0
        size = min(size, max_size_by_price * 0.1)

        if entry_price > 1000:
            size = min(size, 10)
        elif entry_price > 100:
            size = min(size, 100)
        elif entry_price > 10:
            size = min(size, 1000)
        else:
            size = min(size, 10000)

        return max(size, 1.0)


class VolatilityTargetPositionSizer(PositionSizingModel):
    """
    Volatility-targeted Position Sizing
    Adjusts position size inversely to volatility
    """
    def __init__(self, target_volatility: float = 0.02):  # 2% target volatility
        self.target_volatility = target_volatility

    def compute_size(self, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float,
                     volatility: Optional[float] = None,
                     signal_expectancy: Optional[float] = None,
                     regime_accuracy: Optional[float] = None,
                     fusion_confidence: Optional[float] = None,
                     correlation_exposure: Optional[float] = None,
                     current_drawdown: Optional[float] = None,
                     **kwargs) -> float:
        """
        Calculate position size to achieve target volatility
        """
        if volatility is None or volatility <= 0:
            # Use stop loss distance as volatility proxy if not provided
            volatility = abs(entry_price - stop_loss)
            if volatility <= 0:
                return 1.0  # Default minimum size

        # Calculate position size to achieve target volatility
        size = (portfolio_equity * self.target_volatility) / volatility

        # Adjust size based on additional factors
        if signal_expectancy is not None:
            expectancy_factor = 0.5 + (signal_expectancy + 1.0) / 2.0
            size *= expectancy_factor

        if regime_accuracy is not None:
            size *= regime_accuracy

        if fusion_confidence is not None:
            size *= fusion_confidence

        if correlation_exposure is not None:
            correlation_penalty = max(0.1, 1.0 - correlation_exposure)
            size *= correlation_penalty

        if current_drawdown is not None:
            drawdown_factor = max(0.1, 1.0 - current_drawdown)
            size *= drawdown_factor

        # Apply constraints to prevent unrealistic positions
        max_size_by_price = portfolio_equity / entry_price if entry_price > 0 else 1.0
        size = min(size, max_size_by_price * 0.1)

        if entry_price > 1000:
            size = min(size, 10)
        elif entry_price > 100:
            size = min(size, 100)
        elif entry_price > 10:
            size = min(size, 1000)
        else:
            size = min(size, 10000)

        return max(size, 1.0)


class ProbabilisticPositionSizer(PositionSizingModel):
    """
    Probabilistic Position Sizing
    Uses signal expectancy and other factors to determine position size
    """
    def compute_size(self, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float,
                     volatility: Optional[float] = None,
                     signal_expectancy: Optional[float] = None,
                     regime_accuracy: Optional[float] = None,
                     fusion_confidence: Optional[float] = None,
                     correlation_exposure: Optional[float] = None,
                     current_drawdown: Optional[float] = None,
                     **kwargs) -> float:
        """
        Calculate position size based on probabilistic factors
        """
        # Base risk amount
        risk_amount = portfolio_equity * risk_per_trade

        # Combine all factors to determine final risk amount
        combined_factor = 1.0

        if signal_expectancy is not None:
            # Expectancy should be between -1 and 1, map to 0.1 to 2.0
            expectancy_factor = 0.55 + (signal_expectancy * 0.45)  # Maps -1:+1 to 0.1:1.0
            combined_factor *= expectancy_factor

        if regime_accuracy is not None:
            combined_factor *= regime_accuracy

        if fusion_confidence is not None:
            combined_factor *= fusion_confidence

        if correlation_exposure is not None:
            correlation_penalty = max(0.1, 1.0 - correlation_exposure)
            combined_factor *= correlation_penalty

        if current_drawdown is not None:
            drawdown_factor = max(0.1, 1.0 - current_drawdown)
            combined_factor *= drawdown_factor

        # Apply combined factor to risk amount
        risk_amount *= combined_factor

        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit <= 0:
            risk_per_unit = abs(entry_price - stop_loss) or 0.01  # Small default value

        # Calculate position size
        size = risk_amount / risk_per_unit

        # Apply constraints
        max_size_by_price = portfolio_equity / entry_price if entry_price > 0 else float('inf')
        size = min(size, max_size_by_price * 0.1)

        if entry_price > 1000:
            size = min(size, 10)
        elif entry_price > 100:
            size = min(size, 100)
        elif entry_price > 10:
            size = min(size, 1000)
        else:
            size = min(size, 10000)

        return max(size, 0.01)  # Minimum position size


class PositionSizingService:
    """
    Service to manage multiple position sizing models
    """
    def __init__(self):
        self.models = {
            'fixed_risk': FixedRiskPositionSizer(),
            'kelly': KellyPositionSizer(),
            'atr': ATRBasedPositionSizer(),
            'volatility_target': VolatilityTargetPositionSizer(),
            'probabilistic': ProbabilisticPositionSizer()
        }

    def add_model(self, name: str, model: PositionSizingModel):
        """Add a custom position sizing model"""
        self.models[name] = model

    def compute_size(self, model_name: str, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float,
                     volatility: Optional[float] = None,
                     signal_expectancy: Optional[float] = None,
                     regime_accuracy: Optional[float] = None,
                     fusion_confidence: Optional[float] = None,
                     correlation_exposure: Optional[float] = None,
                     current_drawdown: Optional[float] = None,
                     **kwargs) -> float:
        """Compute position size using the specified model"""
        if model_name not in self.models:
            raise ValueError(f"Position sizing model '{model_name}' not found")

        return self.models[model_name].compute_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            portfolio_equity=portfolio_equity,
            risk_per_trade=risk_per_trade,
            volatility=volatility,
            signal_expectancy=signal_expectancy,
            regime_accuracy=regime_accuracy,
            fusion_confidence=fusion_confidence,
            correlation_exposure=correlation_exposure,
            current_drawdown=current_drawdown,
            **kwargs
        )

    def get_available_models(self) -> list:
        """Get list of available position sizing models"""
        return list(self.models.keys())