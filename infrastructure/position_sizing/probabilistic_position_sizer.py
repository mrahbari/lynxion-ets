"""
Advanced Probabilistic Position Sizing with evidence-weighted approach.
Implements regime-adaptive, correlation-aware, and expectancy-based position sizing.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class PositionSizingMethod(Enum):
    """Different position sizing methods"""
    PROBABILISTIC = "probabilistic"
    KELLY_MODIFIED = "kelly_modified"
    EXPECTANCY_BASED = "expectancy_based"
    CORRELATION_ADJUSTED = "correlation_adjusted"
    REGIME_AWARE = "regime_aware"


@dataclass
class PositionSizeResult:
    """Result container for position sizing"""
    size: float
    confidence: float
    risk_amount: float
    method_used: str
    factors: Dict[str, float]


class EvidenceWeightedPositionSizer:
    """
    Redesigned Position Sizing with probabilistic and evidence-weighted approach.

    Mathematical Formula:
    Position_Size = (Portfolio_Equity * Base_Risk_Percentage * Confidence_Product *
                     Regime_Adjustment * Correlation_Penalty * Drawdown_Adjustment) / Risk_Distance

    Where:
    - Confidence_Product = geometric_mean(fusion_confidence, regime_accuracy, strategy_expectancy)
    - Regime_Adjustment = regime_specific_multiplier
    - Correlation_Penalty = 1 - (avg_correlation_with_portfolio * penalty_factor)
    - Drawdown_Adjustment = exp(-current_drawdown / max_expected_drawdown)
    - Risk_Distance = |entry_price - stop_loss|

    This approach increases profitability by:
    - Expanding position sizes during high-confidence, low-risk periods
    - Contracting position sizes during uncertain periods
    - Maintaining strict risk controls to preserve capital
    """

    def __init__(self,
                 base_risk_percentage: float = 0.01,  # 1% base risk
                 max_position_percentage: float = 0.1,  # 10% max per position
                 min_position_size: float = 0.001,  # Minimum position size
                 correlation_penalty_factor: float = 0.5,  # How much to penalize for correlation
                 max_expected_drawdown: float = 0.20,  # 20% max expected drawdown
                 regime_risk_multipliers: Optional[Dict[str, str]] = None):

        self.base_risk_percentage = base_risk_percentage
        self.max_position_percentage = max_position_percentage
        self.min_position_size = min_position_size
        self.correlation_penalty_factor = correlation_penalty_factor
        self.max_expected_drawdown = max_expected_drawdown

        # Default regime risk multipliers
        self.regime_risk_multipliers = regime_risk_multipliers or {
            "bullish_trending": 1.2,
            "bearish_trending": 1.2,
            "high_volatility": 0.6,
            "low_volatility": 1.1,
            "choppy": 0.5,
            "breakout": 0.8,
            "normal": 1.0
        }

    def calculate_size(self,
                      entry_price: float,
                      stop_loss: float,
                      portfolio_equity: float,
                      fusion_confidence: float,
                      regime_accuracy: float,
                      strategy_expectancy: float,
                      correlation_exposure: float,
                      current_drawdown: float,
                      sl_distance_timeframe_adjusted: float,
                      regime_context: str = "normal",
                      volatility: Optional[float] = None,
                      portfolio_symbols: Optional[List[str]] = None,
                      method: PositionSizingMethod = PositionSizingMethod.PROBABILISTIC) -> PositionSizeResult:
        """
        Calculate position size using probabilistic and evidence-weighted approach.

        Args:
            entry_price: Entry price for the position
            stop_loss: Stop loss price (timeframe-adjusted)
            portfolio_equity: Total portfolio equity
            fusion_confidence: Confidence from fusion engine (0-1)
            regime_accuracy: Accuracy of regime classification (0-1)
            strategy_expectancy: Expected return of strategy (-1 to 1)
            correlation_exposure: Average correlation with portfolio (0-1)
            current_drawdown: Current portfolio drawdown (0-1)
            sl_distance_timeframe_adjusted: Stop loss distance adjusted for timeframe
            regime_context: Current market regime
            volatility: Asset volatility
            portfolio_symbols: List of symbols in portfolio
            method: Position sizing method to use

        Returns:
            PositionSizeResult with calculated size and factors
        """
        # Calculate risk distance (timeframe-adjusted)
        risk_distance = sl_distance_timeframe_adjusted
        if risk_distance <= 0:
            risk_distance = abs(entry_price - stop_loss)
        if risk_distance <= 0:
            risk_distance = entry_price * 0.02  # Default 2% stop if not provided

        # Calculate base risk amount
        base_risk_amount = portfolio_equity * self.base_risk_percentage

        # Calculate confidence product (evidence weighting)
        confidence_product = self._calculate_confidence_product(
            fusion_confidence, regime_accuracy, strategy_expectancy
        )

        # Calculate regime adjustment
        regime_adjustment = self.regime_risk_multipliers.get(regime_context.lower(), 1.0)

        # Calculate correlation penalty
        correlation_penalty = self._calculate_correlation_penalty(correlation_exposure)

        # Calculate drawdown adjustment (reduce position size during drawdowns)
        drawdown_adjustment = self._calculate_drawdown_adjustment(current_drawdown)

        # Calculate volatility adjustment if provided
        volatility_adjustment = self._calculate_volatility_adjustment(volatility)

        # Calculate final risk adjustment
        risk_multiplier = (confidence_product *
                          regime_adjustment *
                          correlation_penalty *
                          drawdown_adjustment *
                          volatility_adjustment)

        # Calculate adjusted risk amount
        adjusted_risk_amount = base_risk_amount * risk_multiplier

        # Calculate position size
        position_size = adjusted_risk_amount / risk_distance

        # Apply constraints
        position_size = self._apply_constraints(
            position_size, entry_price, portfolio_equity, portfolio_symbols or []
        )

        # Prepare factors for transparency
        factors = {
            'base_risk_amount': base_risk_amount,
            'confidence_product': confidence_product,
            'regime_adjustment': regime_adjustment,
            'correlation_penalty': correlation_penalty,
            'drawdown_adjustment': drawdown_adjustment,
            'volatility_adjustment': volatility_adjustment,
            'risk_multiplier': risk_multiplier,
            'risk_distance': risk_distance
        }

        return PositionSizeResult(
            size=max(position_size, self.min_position_size),
            confidence=confidence_product,
            risk_amount=adjusted_risk_amount,
            method_used=method.value,
            factors=factors,
            volatility_adjusted=volatility is not None,
            correlation_adjusted=True,
            regime_adjusted=True
        )

    def _calculate_confidence_product(self,
                                    fusion_confidence: float,
                                    regime_accuracy: float,
                                    strategy_expectancy: float) -> float:
        """
        Calculate confidence product from multiple evidence sources.

        Formula: geometric_mean(fusion_confidence, regime_accuracy, expectancy_factor)
        where expectancy_factor = 0.5 + (strategy_expectancy + 1.0) / 4.0
        """
        # Convert strategy expectancy to confidence-like factor (0-1 range)
        expectancy_factor = 0.5 + (strategy_expectancy + 1.0) / 4.0  # Maps -1:+1 to 0.25:0.75
        expectancy_factor = max(0.1, min(0.9, expectancy_factor))  # Clamp to reasonable range

        # Calculate geometric mean of all confidence factors
        # Using geometric mean to penalize low values more heavily
        confidence_factors = [fusion_confidence, regime_accuracy, expectancy_factor]

        # Geometric mean: (a * b * c)^(1/3)
        geometric_mean = np.prod(confidence_factors) ** (1.0 / len(confidence_factors))

        return geometric_mean

    def _calculate_correlation_penalty(self, correlation_exposure: float) -> float:
        """
        Calculate penalty based on correlation with portfolio.

        Formula: 1 - (correlation_exposure * penalty_factor)
        """
        penalty = correlation_exposure * self.correlation_penalty_factor
        return max(0.1, 1.0 - penalty)  # Don't go below 10% of base risk

    def _calculate_drawdown_adjustment(self, current_drawdown: float) -> float:
        """
        Calculate adjustment based on current drawdown.

        Formula: exp(-drawdown_severity * 3), where drawdown_severity = current_drawdown / max_expected_drawdown
        """
        # Calculate drawdown severity relative to maximum expected
        drawdown_severity = min(current_drawdown / self.max_expected_drawdown, 1.0)

        # Exponential decay: more severe drawdowns get greater risk reduction
        adjustment = np.exp(-drawdown_severity * 3)

        return max(0.05, adjustment)  # Don't go below 5% of base risk

    def _calculate_volatility_adjustment(self, volatility: Optional[float]) -> float:
        """
        Calculate adjustment based on asset volatility.

        Formula: 1 / (1 + normalized_volatility), where normalized_volatility = volatility / baseline
        """
        if volatility is None:
            return 1.0

        baseline_volatility = 0.02  # 2% daily volatility baseline
        normalized_volatility = volatility / baseline_volatility

        # Inverse relationship: higher volatility = lower position size
        adjustment = 1.0 / (1.0 + normalized_volatility)

        return max(0.3, adjustment)  # Don't go below 30% of base risk

    def _apply_constraints(self,
                          position_size: float,
                          entry_price: float,
                          portfolio_equity: float,
                          portfolio_symbols: List[str]) -> float:
        """
        Apply position size constraints.
        """
        # Constraint 1: Maximum position percentage of portfolio
        max_by_portfolio = (portfolio_equity * self.max_position_percentage) / entry_price if entry_price > 0 else float('inf')
        position_size = min(position_size, max_by_portfolio)

        # Constraint 2: Minimum position size
        position_size = max(position_size, self.min_position_size)

        # Constraint 3: Reasonable position size based on asset price
        if entry_price > 1000:
            position_size = min(position_size, 10)  # For expensive assets like BTC
        elif entry_price > 100:
            position_size = min(position_size, 100)  # For mid-range assets like ETH
        elif entry_price > 10:
            position_size = min(position_size, 1000)  # For low-mid range assets
        else:
            position_size = min(position_size, 10000)  # For very low-priced assets

        return position_size

    def calculate_expectancy(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate trading strategy expectancy.

        Formula: (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        Result is normalized to -1 to 1 range
        """
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Normalize to -1 to 1 range (assuming reasonable max values)
        max_possible_expectancy = max(avg_win, avg_loss)  # Approximate upper bound
        if max_possible_expectancy > 0:
            normalized_expectancy = expectancy / max_possible_expectancy
            # Clamp to reasonable range
            return max(-1.0, min(1.0, normalized_expectancy))
        else:
            return 0.0

    def calculate_kelly_fraction(self, win_rate: float, avg_win_rate: float, avg_loss_rate: float) -> float:
        """
        Calculate Kelly fraction for position sizing.

        Formula: (bp - q) / b
        where b = avg_win_rate / avg_loss_rate, p = win_rate, q = 1 - win_rate
        """
        if avg_loss_rate <= 0:
            return self.base_risk_percentage  # Default to base risk if no losses

        b = avg_win_rate / avg_loss_rate  # Win/loss ratio
        p = win_rate
        q = 1 - p

        kelly_fraction = (b * p - q) / b if b > 0 else 0

        # Cap Kelly fraction to prevent overbetting
        kelly_fraction = max(0, min(self.base_risk_percentage * 2, kelly_fraction))

        return kelly_fraction

    def calculate_scalp_size_adjustment(self, timeframe_minutes: int, volatility: float) -> float:
        """
        Calculate position size adjustment for scalping strategies based on timeframe and volatility.

        Scalping strategies must prioritize hit probability and time efficiency over large RR.
        """
        if timeframe_minutes > 15:  # Not a scalping timeframe
            return 1.0

        # For scalping, reduce position size to manage risk more carefully
        # due to higher frequency and shorter holding periods
        scalp_adjustment = 0.7  # Reduce by 30% for scalping

        # Further adjust based on volatility - higher volatility means smaller positions
        volatility_factor = max(0.5, 1.0 - (volatility / 0.05))  # Reduce as volatility increases

        return scalp_adjustment * volatility_factor


class ProbabilisticPositionSizer:
    """
    Advanced position sizing with probabilistic and evidence-weighted approach.

    Formula: Position_Size = (Portfolio_Equity * Base_Risk * Confidence_Product * Regime_Adjustment * Correlation_Penalty) / Risk_Distance

    Where:
    - Confidence_Product = fusion_confidence * regime_accuracy * strategy_expectancy
    - Regime_Adjustment = regime_specific_multiplier
    - Correlation_Penalty = 1 - avg_correlation_with_portfolio
    - Risk_Distance = |entry_price - stop_loss|
    """

    def __init__(self,
                 base_risk_percentage: float = 0.01,  # 1% base risk
                 max_position_percentage: float = 0.1,  # 10% max per position
                 min_position_size: float = 0.001,  # Minimum position size
                 correlation_penalty_factor: float = 0.5,  # How much to penalize for correlation
                 regime_risk_multipliers: Optional[Dict[str, float]] = None):

        self.base_risk_percentage = base_risk_percentage
        self.max_position_percentage = max_position_percentage
        self.min_position_size = min_position_size
        self.correlation_penalty_factor = correlation_penalty_factor

        # Default regime risk multipliers
        self.regime_risk_multipliers = regime_risk_multipliers or {
            "bullish_trending": 1.2,
            "bearish_trending": 1.2,
            "high_volatility": 0.6,
            "low_volatility": 1.1,
            "choppy": 0.5,
            "breakout": 0.8,
            "normal": 1.0
        }

    def calculate_size(self,
                      entry_price: float,
                      stop_loss: float,
                      portfolio_equity: float,
                      fusion_confidence: float,
                      regime_accuracy: float,
                      strategy_expectancy: float,
                      correlation_exposure: float,
                      current_drawdown: float,
                      regime_context: str = "normal",
                      volatility: Optional[float] = None,
                      portfolio_symbols: Optional[List[str]] = None,
                      method: PositionSizingMethod = PositionSizingMethod.PROBABILISTIC) -> PositionSizeResult:
        """
        Calculate position size using probabilistic and evidence-weighted approach.
        
        Args:
            entry_price: Entry price for the position
            stop_loss: Stop loss price
            portfolio_equity: Total portfolio equity
            fusion_confidence: Confidence from fusion engine (0-1)
            regime_accuracy: Accuracy of regime classification (0-1)
            strategy_expectancy: Expected return of strategy (-1 to 1)
            correlation_exposure: Average correlation with portfolio (0-1)
            current_drawdown: Current portfolio drawdown (0-1)
            regime_context: Current market regime
            volatility: Asset volatility
            portfolio_symbols: List of symbols in portfolio
            method: Position sizing method to use
            
        Returns:
            PositionSizeResult with calculated size and factors
        """
        # Calculate risk distance
        risk_distance = abs(entry_price - stop_loss)
        if risk_distance <= 0:
            risk_distance = entry_price * 0.02  # Default 2% stop if not provided

        # Calculate base risk amount
        base_risk_amount = portfolio_equity * self.base_risk_percentage

        # Calculate confidence product (evidence weighting)
        confidence_product = self._calculate_confidence_product(
            fusion_confidence, regime_accuracy, strategy_expectancy
        )

        # Calculate regime adjustment
        regime_adjustment = self.regime_risk_multipliers.get(regime_context.lower(), 1.0)

        # Calculate correlation penalty
        correlation_penalty = self._calculate_correlation_penalty(correlation_exposure)

        # Calculate drawdown adjustment (reduce position size during drawdowns)
        drawdown_adjustment = self._calculate_drawdown_adjustment(current_drawdown)

        # Calculate volatility adjustment if provided
        volatility_adjustment = self._calculate_volatility_adjustment(volatility)

        # Calculate final risk adjustment
        risk_multiplier = (confidence_product * 
                          regime_adjustment * 
                          correlation_penalty * 
                          drawdown_adjustment * 
                          volatility_adjustment)

        # Calculate adjusted risk amount
        adjusted_risk_amount = base_risk_amount * risk_multiplier

        # Calculate position size
        position_size = adjusted_risk_amount / risk_distance

        # Apply constraints
        position_size = self._apply_constraints(
            position_size, entry_price, portfolio_equity, portfolio_symbols or []
        )

        # Prepare factors for transparency
        factors = {
            'base_risk_amount': base_risk_amount,
            'confidence_product': confidence_product,
            'regime_adjustment': regime_adjustment,
            'correlation_penalty': correlation_penalty,
            'drawdown_adjustment': drawdown_adjustment,
            'volatility_adjustment': volatility_adjustment,
            'risk_multiplier': risk_multiplier,
            'risk_distance': risk_distance
        }

        return PositionSizeResult(
            size=max(position_size, self.min_position_size),
            confidence=confidence_product,
            risk_amount=adjusted_risk_amount,
            method_used=method.value,
            factors=factors
        )

    def _calculate_confidence_product(self, 
                                    fusion_confidence: float, 
                                    regime_accuracy: float, 
                                    strategy_expectancy: float) -> float:
        """
        Calculate confidence product from multiple evidence sources.
        
        Formula: geometric_mean(fusion_confidence, regime_accuracy, expectancy_factor)
        where expectancy_factor = 0.5 + (strategy_expectancy + 1.0) / 4.0
        """
        # Convert strategy expectancy to confidence-like factor (0-1 range)
        expectancy_factor = 0.5 + (strategy_expectancy + 1.0) / 4.0  # Maps -1:+1 to 0.25:0.75
        expectancy_factor = max(0.1, min(0.9, expectancy_factor))  # Clamp to reasonable range

        # Calculate geometric mean of all confidence factors
        # Using geometric mean to penalize low values more heavily
        confidence_factors = [fusion_confidence, regime_accuracy, expectancy_factor]
        
        # Geometric mean: (a * b * c)^(1/3)
        geometric_mean = np.prod(confidence_factors) ** (1.0 / len(confidence_factors))
        
        return geometric_mean

    def _calculate_correlation_penalty(self, correlation_exposure: float) -> float:
        """
        Calculate penalty based on correlation with portfolio.
        
        Formula: 1 - (correlation_exposure * penalty_factor)
        """
        penalty = correlation_exposure * self.correlation_penalty_factor
        return max(0.1, 1.0 - penalty)  # Don't go below 10% of base risk

    def _calculate_drawdown_adjustment(self, current_drawdown: float) -> float:
        """
        Calculate adjustment based on current drawdown.
        
        Formula: exp(-drawdown_severity * 3), where drawdown_severity = current_drawdown / max_expected_drawdown
        """
        # Assume max expected drawdown is 20% for this calculation
        max_expected_drawdown = 0.20
        drawdown_severity = min(current_drawdown / max_expected_drawdown, 1.0)
        
        # Exponential decay: more severe drawdowns get greater risk reduction
        adjustment = np.exp(-drawdown_severity * 3)
        
        return max(0.05, adjustment)  # Don't go below 5% of base risk

    def _calculate_volatility_adjustment(self, volatility: Optional[float]) -> float:
        """
        Calculate adjustment based on asset volatility.
        
        Formula: 1 / (1 + normalized_volatility), where normalized_volatility = volatility / baseline
        """
        if volatility is None:
            return 1.0
            
        baseline_volatility = 0.02  # 2% daily volatility baseline
        normalized_volatility = volatility / baseline_volatility
        
        # Inverse relationship: higher volatility = lower position size
        adjustment = 1.0 / (1.0 + normalized_volatility)
        
        return max(0.3, adjustment)  # Don't go below 30% of base risk

    def _apply_constraints(self, 
                          position_size: float, 
                          entry_price: float, 
                          portfolio_equity: float, 
                          portfolio_symbols: List[str]) -> float:
        """
        Apply position size constraints.
        """
        # Constraint 1: Maximum position percentage of portfolio
        max_by_portfolio = (portfolio_equity * self.max_position_percentage) / entry_price if entry_price > 0 else float('inf')
        position_size = min(position_size, max_by_portfolio)
        
        # Constraint 2: Minimum position size
        position_size = max(position_size, self.min_position_size)
        
        # Constraint 3: Reasonable position size based on asset price
        if entry_price > 1000:
            position_size = min(position_size, 10)  # For expensive assets like BTC
        elif entry_price > 100:
            position_size = min(position_size, 100)  # For mid-range assets like ETH
        elif entry_price > 10:
            position_size = min(position_size, 1000)  # For low-mid range assets
        else:
            position_size = min(position_size, 10000)  # For very low-priced assets
        
        return position_size

    def calculate_expectancy(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate trading strategy expectancy.
        
        Formula: (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        Result is normalized to -1 to 1 range
        """
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        # Normalize to -1 to 1 range (assuming reasonable max values)
        max_possible_expectancy = max(avg_win, avg_loss)  # Approximate upper bound
        if max_possible_expectancy > 0:
            normalized_expectancy = expectancy / max_possible_expectancy
            # Clamp to reasonable range
            return max(-1.0, min(1.0, normalized_expectancy))
        else:
            return 0.0

    def calculate_kelly_fraction(self, win_rate: float, avg_win_rate: float, avg_loss_rate: float) -> float:
        """
        Calculate Kelly fraction for position sizing.
        
        Formula: (bp - q) / b
        where b = avg_win_rate / avg_loss_rate, p = win_rate, q = 1 - win_rate
        """
        if avg_loss_rate <= 0:
            return self.base_risk_percentage  # Default to base risk if no losses
            
        b = avg_win_rate / avg_loss_rate  # Win/loss ratio
        p = win_rate
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b if b > 0 else 0
        
        # Cap Kelly fraction to prevent overbetting
        kelly_fraction = max(0, min(self.base_risk_percentage * 2, kelly_fraction))
        
        return kelly_fraction


class AdvancedPositionSizingService:
    """Service to manage multiple position sizing approaches"""

    def __init__(self):
        self.sizer = ProbabilisticPositionSizer()
        self.evidence_weighted_sizer = EvidenceWeightedPositionSizer()
        self.historical_sizes: Dict[str, List[PositionSizeResult]] = {}

    def get_optimal_size(self,
                        symbol: str,
                        entry_price: float,
                        stop_loss: float,
                        portfolio_equity: float,
                        fusion_confidence: float = 0.7,
                        regime_accuracy: float = 0.7,
                        strategy_expectancy: float = 0.1,
                        correlation_exposure: float = 0.2,
                        current_drawdown: float = 0.0,
                        sl_distance_timeframe_adjusted: float = None,
                        regime_context: str = "normal",
                        volatility: Optional[float] = None,
                        timeframe_minutes: int = 60) -> PositionSizeResult:
        """
        Get optimal position size using evidence-weighted approach.
        """
        # Calculate timeframe-adjusted stop loss distance if not provided
        if sl_distance_timeframe_adjusted is None:
            sl_distance_timeframe_adjusted = abs(entry_price - stop_loss)

        # Calculate base position size using evidence-weighted approach
        result = self.evidence_weighted_sizer.calculate_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            portfolio_equity=portfolio_equity,
            fusion_confidence=fusion_confidence,
            regime_accuracy=regime_accuracy,
            strategy_expectancy=strategy_expectancy,
            correlation_exposure=correlation_exposure,
            current_drawdown=current_drawdown,
            sl_distance_timeframe_adjusted=sl_distance_timeframe_adjusted,
            regime_context=regime_context,
            volatility=volatility
        )

        # Apply scalping adjustment if applicable
        if timeframe_minutes <= 15:  # Scalping timeframe
            scalp_adjustment = self.evidence_weighted_sizer.calculate_scalp_size_adjustment(timeframe_minutes, volatility or 0.02)
            adjusted_size = result.size * scalp_adjustment

            # Update the result with the adjusted size
            result = PositionSizeResult(
                size=adjusted_size,
                confidence=result.confidence,
                risk_amount=result.risk_amount * scalp_adjustment,
                method_used=result.method_used,
                factors=result.factors,
                volatility_adjusted=result.volatility_adjusted,
                correlation_adjusted=result.correlation_adjusted,
                regime_adjusted=result.regime_adjusted
            )

        # Store for historical analysis
        if symbol not in self.historical_sizes:
            self.historical_sizes[symbol] = []
        self.historical_sizes[symbol].append(result)

        return result
    
    def get_historical_performance(self, symbol: str) -> Dict[str, Any]:
        """Get historical performance metrics for a symbol."""
        if symbol not in self.historical_sizes or not self.historical_sizes[symbol]:
            return {}
        
        sizes = [r.size for r in self.historical_sizes[symbol]]
        confidences = [r.confidence for r in self.historical_sizes[symbol]]
        risk_amounts = [r.risk_amount for r in self.historical_sizes[symbol]]
        
        return {
            'avg_size': np.mean(sizes),
            'std_size': np.std(sizes),
            'avg_confidence': np.mean(confidences),
            'avg_risk_amount': np.mean(risk_amounts),
            'total_positions': len(sizes),
            'latest_size': sizes[-1] if sizes else 0
        }


# Global instance
position_sizing_service = AdvancedPositionSizingService()