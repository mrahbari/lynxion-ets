"""
Strategy Adapters for the Enterprise Hedge Fund Trading System
Following hexagonal architecture principles with proper separation of concerns.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from decimal import Decimal
import numpy as np
import pandas as pd
from datetime import datetime

from domain.entities.signal_entities import FusedSignal, ExecutionIntent
from domain.value_objects import Symbol, Percentage, Money
from domain.ports.strategy_ports import StrategyPort
from shared.logger import EnhancedLogger
from infrastructure.strategies.strategy_config import StrategyConfig
from infrastructure.logging.forensic_logger import forensic_logger
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager


class BaseStrategyAdapter(StrategyPort):
    """Base class for strategy adapters implementing StrategyPort"""

    def __init__(self, name: str):
        self.name = name
        self.logger = EnhancedLogger(f"Strategy_{name}")
        self.active = True
        # Get configuration using the standardized config system
        self.config = {
            'enabled': StrategyConfig.get_strategy_enabled(name),
            'max_position_size': StrategyConfig.get_strategy_max_position_size(name, 0.05),
            'min_confidence': StrategyConfig.get_strategy_min_confidence(name, 0.3),
            'max_confidence': StrategyConfig.get_strategy_max_confidence(name, 0.95),
            'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade(name, 0.02),
            'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier(name, 1.5),
            'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier(name, 2.0),
            'lookback_period': StrategyConfig.get_strategy_lookback_period(name, 50),
            'timeframe': StrategyConfig.get_strategy_timeframe(name, '1h')
        }

        # Initialize with default risk parameters
        self.risk_parameters = {
            'max_position_size': self.config['max_position_size'],
            'stop_loss_pct': 0.02,      # 2% stop loss
            'take_profit_pct': 0.03     # 3% take profit
        }

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal and return execution intent if strategy accepts it"""
        # Check if strategy is enabled before processing
        if not StrategyConfig.get_strategy_enabled(self.name):
            self.logger.debug(f"Strategy {self.name} is disabled, skipping signal evaluation")
            return None

        if not self.should_execute(fused_signal):
            self.logger.info(f"Strategy {self.name} rejected fused signal for {fused_signal.symbol.value}")
            return None

        # Select appropriate strategy based on the fused signal
        strategy_name = self.select_strategy(fused_signal)

        # Request risk parameters from the strategy perspective (these will be validated by risk manager)
        risk_parameters = self._calculate_comprehensive_risk_parameters(fused_signal)

        # Create execution intent
        execution_intent = ExecutionIntent(
            symbol=fused_signal.symbol,
            strategy_name=strategy_name,
            side=self._determine_side(fused_signal),
            intent_confidence=Percentage(min(Decimal('1.0'),
                                          max(Decimal('0.0'),
                                              fused_signal.confidence.value * Decimal('0.8')))),  # Slightly reduce confidence
            risk_parameters=risk_parameters,
            timestamp=datetime.now(),
            fused_signal=fused_signal,
            metadata={
                'strategy_reasoning': f'Signal aligned with {strategy_name} strategy criteria',
                'dominant_bias': fused_signal.dominant_bias.value,
                'regime_context': fused_signal.regime_context
            }
        )

        # The risk parameters contain the requested SL/TP values which will be processed by the risk manager
        # However, we need to ensure that the execution intent has the SL/TP prices attached so the broker can use them
        # The risk manager will ultimately validate and potentially adjust these values
        execution_intent.stop_loss_price = Money(
            amount=Decimal('0'),  # Placeholder - will be set by risk manager during position entry
            currency='USDT'
        )

        execution_intent.take_profit_price = Money(
            amount=Decimal('0'),  # Placeholder - will be set by risk manager during position entry
            currency='USDT'
        )

        # Generate trade ID for this execution
        trade_id = forensic_logger._generate_trade_id(fused_signal.symbol.value, getattr(fused_signal, 'exchange', 'BINANCE'))

        self.logger.info(f"Strategy {self.name} accepted fused signal for {fused_signal.symbol.value} "
                        f"with intent confidence {float(execution_intent.intent_confidence.value):.2%}")

        # Prepare detailed strategy decision information for forensic logging
        decision_reasons = {
            'fused_signal_direction': fused_signal.direction,
            'fused_signal_dominant_bias': fused_signal.dominant_bias.value if hasattr(fused_signal.dominant_bias, 'value') else str(fused_signal.dominant_bias),
            'fused_signal_regime_context': fused_signal.regime_context,
            'fused_signal_confidence': float(fused_signal.confidence.value),
            'filters_passed': True,  # Would be determined by actual filter checks
            'risk_profile_requested': risk_parameters,
            'selected_strategy': self.select_strategy(fused_signal)
        }

        # Identify which fusion outputs were used
        fusion_outputs_used = {
            'regime_context': fused_signal.regime_context,
            'dominant_bias': fused_signal.dominant_bias.value if hasattr(fused_signal.dominant_bias, 'value') else str(fused_signal.dominant_bias),
            'direction': fused_signal.direction,
            'confidence': float(fused_signal.confidence.value),
            'dominance_score': fused_signal.dominance_score
        }

        # Log the strategy decision to forensic log with enhanced details
        forensic_logger.log_strategy_decision(
            strategy=self.name,
            symbol=fused_signal.symbol.value,
            exchange=getattr(fused_signal, 'exchange', 'BINANCE'),
            decision=self._determine_side(fused_signal).name if hasattr(self._determine_side(fused_signal), 'name') else str(self._determine_side(fused_signal)),
            confidence=float(execution_intent.intent_confidence.value),
            trade_id=trade_id,
            decision_reasons=decision_reasons,
            fusion_outputs_used=fusion_outputs_used,
            timestamp=execution_intent.timestamp
        )

        # Add trade_id to execution intent metadata
        execution_intent.metadata['trade_id'] = trade_id

        return execution_intent

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Check if the strategy should execute based on the fused signal"""
        # First check if strategy is enabled
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        # Get strategy-specific configuration
        min_confidence = self.config['min_confidence']

        # Check signal confidence against strategy threshold
        confidence = float(fused_signal.confidence.value)

        # Log rejection reason if confidence is insufficient
        if confidence < min_confidence:
            self.logger.info(f"Trade rejected: "
                           f"confidence={confidence:.2f} < "
                           f"STRATEGY_MIN_CONFIDENCE_THRESHOLD={min_confidence:.2f} "
                           f"source=strategy_adapter "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False

        return True

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

        # Check for consistency between direction and dominant bias
        direction_side = None
        if fused_signal.direction > 0.1:  # Threshold to avoid neutral signals
            direction_side = OrderSide.BUY
        elif fused_signal.direction < -0.1:
            direction_side = OrderSide.SELL
        else:
            direction_side = None  # Neutral based on direction

        # Get bias side
        bias_side = None
        if fused_signal.dominant_bias.value in ['BUY', 'LONG']:
            bias_side = OrderSide.BUY
        elif fused_signal.dominant_bias.value in ['SELL', 'SHORT']:
            bias_side = OrderSide.SELL
        else:
            bias_side = OrderSide.BUY if fused_signal.direction >= 0 else OrderSide.SELL  # Default to direction

        # If direction and bias agree, use that side
        if direction_side is not None and direction_side == bias_side:
            return direction_side
        elif direction_side is not None and bias_side is not None:
            # If we have both direction and bias but they disagree, check the confidence
            # If the bias is significantly stronger than the direction, consider it
            # For now, we'll log this contradiction and prioritize direction but with reduced confidence
            # In the future, we might want to implement more sophisticated conflict resolution
            direction_strength = abs(fused_signal.direction)
            bias_strength = fused_signal.dominance_score if fused_signal.dominance_score is not None else 0.5

            # If the bias is significantly stronger than the direction, consider the bias
            if bias_strength > direction_strength * 1.5:  # Bias is 50% stronger than direction
                self.logger.warning(f"Contradictory signal: Direction={fused_signal.direction:.3f}({direction_side.name}) "
                                  f"vs Bias={fused_signal.dominant_bias.value}({bias_side.name}), "
                                  f"bias stronger (score: {bias_strength:.3f} vs {direction_strength:.3f}). "
                                  f"Prioritizing bias direction.")
                return bias_side
            else:
                # Direction is stronger or comparable, but log the contradiction
                self.logger.warning(f"Contradictory signal: Direction={fused_signal.direction:.3f}({direction_side.name}) "
                                  f"vs Bias={fused_signal.dominant_bias.value}({bias_side.name}). "
                                  f"Prioritizing direction but noting conflict.")
                return direction_side
        elif direction_side is not None:
            # If we only have direction, use it
            return direction_side
        else:
            # Use bias as fallback
            return bias_side

    def _calculate_comprehensive_risk_parameters(self, fused_signal: FusedSignal, risk_manager: EnterpriseRiskManager = None) -> Dict[str, Any]:
        """Calculate comprehensive risk parameters based on the fused signal using advanced risk management"""
        # Get strategy-specific configuration
        current_price = 1.0  # Default price if not available
        if hasattr(fused_signal, 'price_data') and hasattr(fused_signal.price_data, 'current_price'):
            current_price = fused_signal.price_data.current_price
        elif hasattr(fused_signal, 'close_price'):
            current_price = fused_signal.close_price
        else:
            # Try to get price from other possible attributes
            for attr in ['current_price', 'close', 'price', 'last_price']:
                if hasattr(fused_signal, attr):
                    current_price = getattr(fused_signal, attr)
                    if isinstance(current_price, (int, float)):
                        break

        # If no risk manager is provided, we'll return basic parameters that will be processed by the risk manager later
        # This ensures that the Strategy module only requests risk parameters but doesn't calculate them
        confidence_factor = float(fused_signal.confidence.value)

        # Calculate requested position size based on confidence (this will be validated by risk manager)
        requested_position_size = min(
            self.config['max_position_size'],
            self.config['max_position_size'] * confidence_factor
        )

        # Strategy should only request risk parameters, not calculate them
        # The actual calculation will be done by the risk manager
        risk_parameters = {
            'requested_position_size': requested_position_size,
            'strategy_confidence': confidence_factor,
            'regime_context': fused_signal.regime_context,
            'max_position_size': self.config['max_position_size'],
            'risk_per_trade': self.config['risk_per_trade'],
            'strategy_name': self.name,
            'symbol': fused_signal.symbol.value if hasattr(fused_signal.symbol, 'value') else str(fused_signal.symbol)
        }

        return risk_parameters


class TrendFollowingStrategy(BaseStrategyAdapter):
    """Trend following strategy implementation"""

    def __init__(self):
        super().__init__("trend_following")
        self.lookback_period = 50
        self.ma_period = 20
        self.trend_strength_threshold = 0.01

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Specific implementation for trend following strategy"""
        # First check if strategy is enabled
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        # Get strategy-specific configuration
        min_confidence = self.config['min_confidence']

        # Check if signal meets trend-following criteria
        confidence = float(fused_signal.confidence.value)
        is_trending = 'trend' in fused_signal.regime_context.lower()
        has_direction = abs(fused_signal.direction) > 0.1

        # Log specific rejection reason
        if confidence < min_confidence:
            self.logger.info(f"Trade rejected: "
                           f"confidence={confidence:.2f} < "
                           f"TREND_FOLLOWING_MIN_CONFIDENCE_THRESHOLD={min_confidence:.2f} "
                           f"source=trend_following_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False
        elif not is_trending:
            self.logger.info(f"Trade rejected: "
                           f"regime_context='{fused_signal.regime_context}' does not indicate trending market "
                           f"source=trend_following_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False
        elif not has_direction:
            self.logger.info(f"Trade rejected: "
                           f"direction={fused_signal.direction:.3f} is too weak (abs<{0.1}) "
                           f"source=trend_following_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False

        return True


class MeanReversionStrategy(BaseStrategyAdapter):
    """Mean reversion strategy implementation"""

    def __init__(self):
        super().__init__("mean_reversion")
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Specific implementation for mean reversion strategy"""
        # First check if strategy is enabled
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        # Get strategy-specific configuration
        min_confidence = self.config['min_confidence']

        # Check if signal meets mean reversion criteria
        confidence = float(fused_signal.confidence.value)
        is_reverting = 'mean' in fused_signal.regime_context.lower() or 'revert' in fused_signal.regime_context.lower()

        # Log specific rejection reason
        if confidence < min_confidence:
            self.logger.info(f"Trade rejected: "
                           f"confidence={confidence:.2f} < "
                           f"MEAN_REVERSION_MIN_CONFIDENCE_THRESHOLD={min_confidence:.2f} "
                           f"source=mean_reversion_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False
        elif not is_reverting:
            self.logger.info(f"Trade rejected: "
                           f"regime_context='{fused_signal.regime_context}' does not indicate mean reversion "
                           f"source=mean_reversion_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False

        return True


class VolatilityBreakoutStrategy(BaseStrategyAdapter):
    """Volatility breakout strategy implementation"""

    def __init__(self):
        super().__init__("volatility_breakout")
        self.atr_period = 14
        self.atr_multiplier = 1.5

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Specific implementation for volatility breakout strategy"""
        # First check if strategy is enabled
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        # Get strategy-specific configuration
        min_confidence = self.config['min_confidence']

        # Check if signal meets volatility breakout criteria
        confidence = float(fused_signal.confidence.value)
        is_volatile = 'volatile' in fused_signal.regime_context.lower() or 'breakout' in fused_signal.regime_context.lower()

        # Log specific rejection reason
        if confidence < min_confidence:
            self.logger.info(f"Trade rejected: "
                           f"confidence={confidence:.2f} < "
                           f"VOLATILITY_BREAKOUT_MIN_CONFIDENCE_THRESHOLD={min_confidence:.2f} "
                           f"source=volatility_breakout_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False
        elif not is_volatile:
            self.logger.info(f"Trade rejected: "
                           f"regime_context='{fused_signal.regime_context}' does not indicate volatility breakout "
                           f"source=volatility_breakout_strategy "
                           f"strategy={self.name} "
                           f"symbol={fused_signal.symbol.value}")
            return False

        return True