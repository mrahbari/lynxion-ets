"""
Infrastructure implementation of Strategy adapters for the enterprise hedge fund trading system.
Following hexagonal architecture principles.
"""
from typing import List, Optional, Dict, Any
from domain.entities.signal_entities import FusedSignal, ExecutionIntent
from domain.value_objects import Symbol, Percentage, Money
from domain.ports.strategy_ports import StrategyPort
from shared.logger import EnhancedLogger
from datetime import datetime
from decimal import Decimal


class BaseStrategyAdapter(StrategyPort):
    """Base class for strategy adapters implementing StrategyPort"""

    def __init__(self, name: str):
        self.name = name
        self.logger = EnhancedLogger(f"Strategy_{name}")
        self.active = True
        self.risk_parameters = {
            'max_position_size': 0.02,  # 2% of portfolio
            'stop_loss_pct': 0.02,      # 2% stop loss
            'take_profit_pct': 0.03     # 3% take profit
        }

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal and return execution intent if strategy accepts it"""
        if not self.should_execute(fused_signal):
            self.logger.info(f"Strategy {self.name} rejected fused signal for {fused_signal.symbol.value}")
            return None

        # Select appropriate strategy based on the fused signal
        strategy_name = self.select_strategy(fused_signal)

        # Create execution intent
        execution_intent = ExecutionIntent(
            symbol=fused_signal.symbol,
            strategy_name=strategy_name,
            side=self._determine_side(fused_signal),
            intent_confidence=Percentage(min(Decimal('1.0'),
                                          max(Decimal('0.0'),
                                              fused_signal.confidence.value * Decimal('0.8')))),  # Slightly reduce confidence
            risk_parameters=self._calculate_risk_parameters(fused_signal),
            timestamp=datetime.now(),
            fused_signal=fused_signal,
            metadata={
                'strategy_reasoning': f'Signal aligned with {strategy_name} strategy criteria',
                'dominant_bias': fused_signal.dominant_bias.value,
                'regime_context': fused_signal.regime_context
            }
        )

        self.logger.info(f"Strategy {self.name} accepted fused signal for {fused_signal.symbol.value} "
                        f"with intent confidence {float(execution_intent.intent_confidence.value):.2%}")
        
        return execution_intent

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Check if the strategy should execute based on the fused signal"""
        # Default implementation: execute based on confidence and signal type with intelligent evaluation
        import os

        # Get configuration thresholds
        min_confidence = float(os.getenv('STRATEGY_MIN_CONFIDENCE_THRESHOLD', '0.3'))  # Minimum confidence to consider
        high_confidence_threshold = float(os.getenv('STRATEGY_HIGH_CONFIDENCE_THRESHOLD', '0.7'))  # High confidence threshold
        neutral_buffer = float(os.getenv('STRATEGY_NEUTRAL_BUFFER', '0.1'))  # Buffer around neutral signals

        confidence = float(fused_signal.confidence.value)

        # Check if signal is not neutral
        is_not_neutral = fused_signal.dominant_bias.value not in ['HOLD', 'NEUTRAL']

        # For high confidence signals, execute regardless of other factors (within reason)
        if confidence >= high_confidence_threshold and is_not_neutral:
            return True

        # For medium confidence signals, apply more nuanced evaluation
        elif confidence >= min_confidence and is_not_neutral:
            # Additional evaluation logic for medium confidence signals
            # Consider the dominance score and regime context
            dominance_score = getattr(fused_signal, 'dominance_score', 0.0)

            # If the dominance score is strong relative to confidence, it's more reliable
            if abs(dominance_score) > (confidence - neutral_buffer):
                return True

            # If the signal is in a favorable regime context, consider it
            regime_context = getattr(fused_signal, 'regime_context', '').lower()
            if any(favorable in regime_context for favorable in ['trend', 'breakout', 'momentum']):
                return True

            # Default to execute for medium confidence non-neutral signals
            return True

        # For low confidence signals, be more selective
        elif confidence < min_confidence and is_not_neutral:
            # Only execute if there are strong supporting factors
            dominance_score = getattr(fused_signal, 'dominance_score', 0.0)
            regime_context = getattr(fused_signal, 'regime_context', '').lower()

            # Execute if dominance is very strong relative to confidence
            if abs(dominance_score) > (min_confidence + 0.2) and any(favorable in regime_context for favorable in ['confirmed', 'strong']):
                return True

            return False

        # Neutral signals should not be executed regardless of confidence
        else:
            return False

    def select_strategy(self, fused_signal: FusedSignal) -> str:
        """Select the appropriate strategy based on the fused signal and market conditions"""
        # Default implementation - in real system this would be more sophisticated
        regime = fused_signal.regime_context.lower()
        
        if 'trend' in regime:
            return 'trend_following'
        elif 'mean' in regime or 'revert' in regime:
            return 'mean_reversion'
        elif 'volatile' in regime:
            return 'volatility_breakout'
        elif 'momentum' in regime:
            return 'momentum_strategy'
        else:
            return 'balanced_strategy'

    def get_strategy_name(self) -> str:
        """Get the name of this strategy"""
        return self.name

    def get_strategy_type(self) -> str:
        """Get the type of this strategy for classification"""
        return self.__class__.__name__

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update strategy with new market data"""
        # Base implementation - can be overridden by specific strategies
        pass

    def _determine_side(self, fused_signal: FusedSignal):
        """Determine order side based on fused signal direction"""
        from domain.entities.signal_entities import OrderSide
        
        if fused_signal.direction > 0.1:  # Threshold to avoid neutral signals
            return OrderSide.BUY
        elif fused_signal.direction < -0.1:
            return OrderSide.SELL
        else:
            # Use dominant bias as fallback
            if fused_signal.dominant_bias.value in ['BUY', 'LONG']:
                return OrderSide.BUY
            else:
                return OrderSide.SELL

    def _calculate_risk_parameters(self, fused_signal: FusedSignal) -> Dict[str, Any]:
        """Calculate risk parameters based on the fused signal"""
        base_risk_params = self.risk_parameters.copy()
        
        # Adjust risk based on signal confidence
        confidence_factor = float(fused_signal.confidence.value)
        base_risk_params['max_position_size'] *= confidence_factor
        base_risk_params['stop_loss_pct'] *= (1.0 + (1.0 - confidence_factor))  # Tighter stops for lower confidence
        
        return base_risk_params


class TrendFollowingStrategy(BaseStrategyAdapter):
    """Strategy for following market trends"""

    def __init__(self):
        super().__init__("trend_following")

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Only execute in trending market conditions"""
        return (super().should_execute(fused_signal) and
                'trend' in fused_signal.regime_context.lower())


class MeanReversionStrategy(BaseStrategyAdapter):
    """Strategy for mean reversion opportunities"""

    def __init__(self):
        super().__init__("mean_reversion")

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Only execute in mean-reverting market conditions"""
        return (super().should_execute(fused_signal) and
                ('mean' in fused_signal.regime_context.lower() or
                 'revert' in fused_signal.regime_context.lower()))


class VolatilityBreakoutStrategy(BaseStrategyAdapter):
    """Strategy for volatility breakout opportunities"""

    def __init__(self):
        super().__init__("volatility_breakout")

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Only execute in high volatility conditions"""
        return (super().should_execute(fused_signal) and
                'volatile' in fused_signal.regime_context.lower())