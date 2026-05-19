"""
Strategy Adapters for the Enterprise Hedge Fund Trading System
Following hexagonal architecture principles with proper separation of concerns.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from decimal import Decimal
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from domain.entities.signal_entities import FusedSignal, ExecutionIntent
from domain.value_objects import Symbol, Percentage, Money
from domain.ports.strategy_ports import StrategyPort
from shared.logger import EnhancedLogger
from infrastructure.strategies.strategy_config import StrategyConfig
from infrastructure.logging.forensic_logger import forensic_logger
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager


class BaseStrategyAdapter(StrategyPort):
    """Base class for strategy adapters implementing StrategyPort with intent discipline"""

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
            'timeframe': StrategyConfig.get_strategy_timeframe(name, '1h'),
            # New configuration for intent discipline
            'min_bars_between_entries': StrategyConfig.get_strategy_min_bars_between_entries(name, 5),
            'max_trades_per_day': StrategyConfig.get_strategy_max_trades_per_day(name, 10),
            'max_consecutive_losses': StrategyConfig.get_strategy_max_consecutive_losses(name, 3),
            'min_atr_threshold': StrategyConfig.get_strategy_min_atr_threshold(name, 0.001),
            'avoid_flat_markets': StrategyConfig.get_strategy_avoid_flat_markets(name, True),
            'cooldown_after_exit_minutes': StrategyConfig.get_strategy_cooldown_after_exit_minutes(name, 30)
        }

        # Initialize with default risk parameters
        self.risk_parameters = {
            'max_position_size': self.config.get('max_position_size', 0.05),
            'stop_loss_pct': 0.02,      # 2% stop loss
            'take_profit_pct': 0.03     # 3% take profit
        }

        # Initialize intent discipline tracking
        self.last_intent_timestamp = {}  # Track last intent per symbol
        self.intent_count_today = {}     # Track daily intent count per symbol
        self.consecutive_losses = {}     # Track consecutive losses per symbol
        self.last_entry_bar_index = {}   # Track last entry bar index per symbol
        self.current_positions = {}      # Track current positions per symbol (TEMPORARY - will be phased out)
        self.last_exit_time = {}         # Track last exit time per symbol for cooldown
        self.bar_counter = {}            # Track bar count per symbol for cooldown
        self.last_signal_conditions = {} # Track last signal conditions to avoid repetition

    def evaluate_fused_signal(self, fused_signal: FusedSignal) -> Optional[ExecutionIntent]:
        """Evaluate a fused signal and return execution intent if strategy accepts it"""
        # Check if strategy is enabled before processing
        if not StrategyConfig.get_strategy_enabled(self.name):
            self.logger.debug(f"Strategy {self.name} is disabled, skipping signal evaluation")
            return None

        # Increment bar counter for this symbol to track timing between entries
        symbol = fused_signal.symbol.value
        self.increment_bar_counter(symbol)

        # Check intent discipline rules before proceeding
        should_emit, reason = self._should_emit_intent(fused_signal)
        if not should_emit:
            self.logger.info(f"Strategy {self.name} blocked intent emission for {symbol}: {reason}")
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

        # Record the intent emission for discipline tracking
        self.record_intent_emission(fused_signal, execution_intent)

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

    def _should_emit_intent(self, fused_signal: FusedSignal) -> tuple[bool, str]:
        """
        Determine if the strategy should emit an intent based on discipline rules.
        NOTE: Position tracking has been removed as strategies should not own position state.
        Position existence is evaluated downstream by execution layer.

        Returns:
            tuple[bool, str]: (should_emit, reason_for_blocking)
        """
        symbol = fused_signal.symbol.value

        # 1. Check minimum bars between entries (LEGITIMATE - timing discipline)
        if not self._passes_min_bars_check(symbol):
            return False, f"Insufficient bars elapsed since last entry for {symbol}"

        # 2. Check daily trade limit (LEGITIMATE - volume discipline)
        if not self._passes_daily_trade_limit_check(symbol):
            return False, f"Daily trade limit exceeded for {symbol}"

        # 3. Check consecutive losses (LEGITIMATE - risk management)
        if not self._passes_consecutive_losses_check(symbol):
            return False, f"Too many consecutive losses for {symbol}, triggering safety pause"

        # 4. Check cooldown after exit (LEGITIMATE - timing discipline)
        if not self._passes_exit_cooldown_check(symbol):
            return False, f"Cooldown period after exit not elapsed for {symbol}"

        # 5. Check market conditions (volatility, flat markets) (LEGITIMATE - market suitability)
        if not self._passes_market_condition_check(fused_signal):
            return False, f"Market conditions not favorable for {symbol}"

        # 6. Check for repeated signals (debouncing) (LEGITIMATE - signal quality)
        if not self._passes_signal_debounce_check(fused_signal):
            return False, f"Repeated signal detected for {symbol}, debouncing"

        # All checks passed
        return True, "All discipline checks passed"

    def _has_open_position(self, symbol: str) -> bool:
        """Check if there's an open position for the given symbol.
        NOTE: This method now always returns False as strategies should not track position state.
        Position state is handled by the execution layer downstream."""
        return False  # Always return False to allow intent emission

    def _passes_min_bars_check(self, symbol: str) -> bool:
        """Check if minimum bars have passed since last entry."""
        min_bars = self.config.get('min_bars_between_entries', 5)  # Use default value of 5 if not specified
        if min_bars <= 0:
            return True

        last_bar_idx = self.last_entry_bar_index.get(symbol, -float('inf'))
        current_bar_idx = self.bar_counter.get(symbol, 0)

        bars_since_last_entry = current_bar_idx - last_bar_idx
        passes_check = bars_since_last_entry >= min_bars

        if not passes_check:
            self.logger.debug(f"Min bars check failed for {symbol}: "
                            f"last_entry_bar={last_bar_idx}, current_bar={current_bar_idx}, "
                            f"bars_since={bars_since_last_entry}, min_required={min_bars}")

        return passes_check

    def _passes_daily_trade_limit_check(self, symbol: str) -> bool:
        """Check if daily trade limit is not exceeded."""
        max_daily_trades = self.config.get('max_trades_per_day', 10)  # Use default value of 10 if not specified
        if max_daily_trades <= 0:
            return True

        today = datetime.now().date()
        daily_count = self.intent_count_today.get((symbol, today), 0)
        passes_check = daily_count < max_daily_trades

        if not passes_check:
            self.logger.debug(f"Daily trade limit check failed for {symbol}: "
                            f"daily_count={daily_count}, limit={max_daily_trades}")

        return passes_check

    def _passes_consecutive_losses_check(self, symbol: str) -> bool:
        """Check if consecutive loss limit is not exceeded."""
        max_consecutive_losses = self.config.get('max_consecutive_losses', 3)  # Use default value of 3 if not specified
        if max_consecutive_losses <= 0:
            return True

        consecutive_loss_count = self.consecutive_losses.get(symbol, 0)
        passes_check = consecutive_loss_count < max_consecutive_losses

        if not passes_check:
            self.logger.debug(f"Consecutive losses check failed for {symbol}: "
                            f"consecutive_losses={consecutive_loss_count}, limit={max_consecutive_losses}")

        return passes_check

    def _passes_exit_cooldown_check(self, symbol: str) -> bool:
        """Check if cooldown period after exit has elapsed."""
        cooldown_minutes = self.config.get('cooldown_after_exit_minutes', 30)  # Use default value of 30 if not specified
        if cooldown_minutes <= 0:
            return True

        last_exit = self.last_exit_time.get(symbol)
        if last_exit is None:
            return True

        time_since_exit = datetime.now() - last_exit
        passes_check = time_since_exit.total_seconds() >= (cooldown_minutes * 60)

        if not passes_check:
            self.logger.debug(f"Exit cooldown check failed for {symbol}: "
                            f"time_since_exit={time_since_exit}, required={cooldown_minutes}min")

        return passes_check

    def _passes_market_condition_check(self, fused_signal: FusedSignal) -> bool:
        """Check if market conditions are favorable for trading."""
        # Check volatility threshold if ATR is available in metadata
        atr_threshold = self.config.get('min_atr_threshold', 0.001)  # Use default value of 0.001 if not specified
        if atr_threshold > 0 and hasattr(fused_signal, 'metadata') and fused_signal.metadata:
            atr_value = fused_signal.metadata.get('atr')
            current_price = fused_signal.metadata.get('current_price') or fused_signal.metadata.get('close_price')

            if atr_value is not None and current_price and current_price > 0:
                atr_pct = atr_value / current_price
                if atr_pct < atr_threshold:
                    self.logger.debug(f"Low volatility check failed for {fused_signal.symbol.value}: "
                                    f"ATR%={atr_pct:.4f}, threshold={atr_threshold:.4f}")
                    return False
            elif atr_value is not None and atr_value < atr_threshold:
                # If current_price is not available but ATR is provided, check ATR directly
                if atr_value < atr_threshold:
                    self.logger.debug(f"Low volatility check failed for {fused_signal.symbol.value}: "
                                    f"ATR={atr_value:.4f}, threshold={atr_threshold:.4f}")
                    return False

        # Check for flat market conditions if available
        if self.config.get('avoid_flat_markets', True) and hasattr(fused_signal, 'metadata') and fused_signal.metadata:
            market_regime = fused_signal.metadata.get('market_regime', '').lower()
            if 'flat' in market_regime or 'sideways' in market_regime:
                self.logger.debug(f"Flat market check failed for {fused_signal.symbol.value}: "
                                f"regime={market_regime}")
                return False

        return True

    def _passes_signal_debounce_check(self, fused_signal: FusedSignal) -> bool:
        """Check if the signal is a repeat of a previous signal."""
        symbol = fused_signal.symbol.value

        # Get current signal characteristics
        current_conditions = {
            'direction': round(fused_signal.direction, 3),  # Round to avoid floating point issues
            'dominant_bias': fused_signal.dominant_bias.value if hasattr(fused_signal.dominant_bias, 'value') else str(fused_signal.dominant_bias),
            'confidence': round(float(fused_signal.confidence.value), 3),
            'regime_context': fused_signal.regime_context
        }

        last_conditions = self.last_signal_conditions.get(symbol)

        # If no previous signal, allow this one
        if last_conditions is None:
            self.last_signal_conditions[symbol] = current_conditions
            return True

        # Check if conditions are essentially the same (debounce repeated signals)
        is_same_direction = abs(last_conditions['direction'] - current_conditions['direction']) < 0.01
        is_same_bias = last_conditions['dominant_bias'] == current_conditions['dominant_bias']
        is_similar_confidence = abs(last_conditions['confidence'] - current_conditions['confidence']) < 0.05
        is_same_regime = last_conditions['regime_context'] == current_conditions['regime_context']

        is_duplicate = is_same_direction and is_same_bias and is_similar_confidence and is_same_regime

        if is_duplicate:
            self.logger.debug(f"Signal debounce check failed for {symbol}: "
                            f"conditions match previous signal")
            return False
        else:
            # Update with new conditions
            self.last_signal_conditions[symbol] = current_conditions
            return True

    def increment_bar_counter(self, symbol: str):
        """Increment the bar counter for a symbol to track timing between entries."""
        current_count = self.bar_counter.get(symbol, -1)  # Start at -1 so first increment gives 0
        self.bar_counter[symbol] = current_count + 1

    def record_intent_emission(self, fused_signal: FusedSignal, execution_intent: ExecutionIntent):
        """Record intent emission for discipline tracking."""
        symbol = fused_signal.symbol.value

        # Update last intent timestamp
        self.last_intent_timestamp[symbol] = datetime.now()

        # Update daily intent count
        today = datetime.now().date()
        daily_key = (symbol, today)
        current_count = self.intent_count_today.get(daily_key, 0)
        self.intent_count_today[daily_key] = current_count + 1

        # Update last entry bar index
        current_bar_idx = self.bar_counter.get(symbol, 0)
        self.last_entry_bar_index[symbol] = current_bar_idx

        # Log the intent emission
        self.logger.info(f"Intent emitted for {symbol}: {execution_intent.side.name} "
                        f"with confidence {float(execution_intent.intent_confidence.value):.2%}")

    def record_position_closed(self, symbol: str):
        """Record that a position has been closed."""
        # Only update exit time and reset consecutive losses - don't modify position state
        self.last_exit_time[symbol] = datetime.now()

        # Reset consecutive losses counter for this symbol
        self.consecutive_losses[symbol] = 0

        self.logger.info(f"Position closed event recorded for {symbol}, updated discipline tracking")

    def force_reset_position_status(self, symbol: str, force_open: bool = False):
        """Force reset the position status for a symbol - useful for testing or correcting state.
        NOTE: This method no longer modifies position state as strategies should not track positions."""
        self.logger.info(f"Position status reset attempt for {symbol} ignored - strategies should not track position state")

    def record_trade_result(self, symbol: str, is_profitable: bool, position_closed: bool = True):
        """Record the result of a trade for consecutive loss tracking."""
        if is_profitable:
            # Reset consecutive losses counter
            self.consecutive_losses[symbol] = 0
        else:
            # Increment consecutive losses counter
            current_losses = self.consecutive_losses.get(symbol, 0)
            self.consecutive_losses[symbol] = current_losses + 1

        # Optionally update exit time after recording the trade result (but don't modify position state)
        if position_closed:
            self.last_exit_time[symbol] = datetime.now()

        self.logger.debug(f"Trade result recorded for {symbol}: {'profit' if is_profitable else 'loss'}, "
                         f"consecutive_losses={self.consecutive_losses[symbol]}, "
                         f"position_closed={position_closed}")

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Check if the strategy should execute based on the fused signal"""
        # First check if strategy is enabled
        if not StrategyConfig.get_strategy_enabled(self.name):
            return False

        # Get strategy-specific configuration
        min_confidence = self.config.get('min_confidence', 0.3)  # Use default value of 0.3 if not specified

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
        max_position_size = self.config.get('max_position_size', 0.05)  # Use default value of 0.05 if not specified
        requested_position_size = min(
            max_position_size,
            max_position_size * confidence_factor
        )

        # Strategy should only request risk parameters, not calculate them
        # The actual calculation will be done by the risk manager
        risk_parameters = {
            'requested_position_size': requested_position_size,
            'strategy_confidence': confidence_factor,
            'regime_context': fused_signal.regime_context,
            'max_position_size': self.config.get('max_position_size', 0.05),
            'risk_per_trade': self.config.get('risk_per_trade', 0.02),
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
        min_confidence = self.config.get('min_confidence', 0.3)  # Use default value of 0.3 if not specified

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
        min_confidence = self.config.get('min_confidence', 0.3)  # Use default value of 0.3 if not specified

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
        min_confidence = self.config.get('min_confidence', 0.3)  # Use default value of 0.3 if not specified

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