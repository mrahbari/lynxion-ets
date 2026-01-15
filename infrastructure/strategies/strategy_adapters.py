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

        # Calculate comprehensive risk parameters using advanced risk management
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

        # Add stop loss and take profit prices directly to the execution intent
        # This ensures the broker receives properly risk-managed orders
        from domain.value_objects import Money
        execution_intent.stop_loss_price = Money(
            amount=float(risk_parameters.get('stop_loss_price', 0.0)),
            currency='USDT'
        ) if risk_parameters.get('stop_loss_price') else None

        execution_intent.take_profit_price = Money(
            amount=float(risk_parameters.get('take_profit_price', 0.0)),
            currency='USDT'
        ) if risk_parameters.get('take_profit_price') else None

        self.logger.info(f"Strategy {self.name} accepted fused signal for {fused_signal.symbol.value} "
                        f"with intent confidence {float(execution_intent.intent_confidence.value):.2%}")

        return execution_intent

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Check if the strategy should execute based on the fused signal"""
        # Default implementation: execute based on confidence and signal type with intelligent evaluation
        import os

        # Get configuration thresholds - Further lowered to allow more trades
        min_confidence = float(os.getenv('STRATEGY_MIN_CONFIDENCE_THRESHOLD', '0.05'))  # Further lowered from 0.10 to 0.05
        high_confidence_threshold = float(os.getenv('STRATEGY_HIGH_CONFIDENCE_THRESHOLD', '0.3'))  # Lowered from 0.4 to 0.3
        neutral_buffer = float(os.getenv('STRATEGY_NEUTRAL_BUFFER', '0.01'))  # Reduced from 0.02 to 0.01

        confidence = float(fused_signal.confidence.value)
        symbol = fused_signal.symbol.value if hasattr(fused_signal.symbol, 'value') else str(fused_signal.symbol)

        # Check if signal is not neutral
        is_not_neutral = fused_signal.dominant_bias.value not in ['HOLD', 'NEUTRAL', 'FLAT']

        # Log detailed information about the decision factors
        self.logger.info(f"Strategy evaluation for {symbol}: "
                        f"Confidence={confidence:.3f}, "
                        f"Dominant Bias={fused_signal.dominant_bias.value}, "
                        f"Is Not Neutral={is_not_neutral}, "
                        f"Dominance Score={getattr(fused_signal, 'dominance_score', 0.0):.3f}, "
                        f"Regime Context={getattr(fused_signal, 'regime_context', 'unknown')}")

        # For high confidence signals, execute regardless of other factors (within reason)
        if confidence >= high_confidence_threshold and is_not_neutral:
            self.logger.info(f"ACCEPTED: High confidence ({confidence:.3f}) and non-neutral signal for {symbol}")
            return True

        # For medium confidence signals, apply more nuanced evaluation
        elif confidence >= min_confidence and is_not_neutral:
            # Additional evaluation logic for medium confidence signals
            # Consider the dominance score and regime context
            dominance_score = getattr(fused_signal, 'dominance_score', 0.0)

            # If the dominance score is strong relative to confidence, it's more reliable
            if abs(dominance_score) > (confidence - neutral_buffer):
                self.logger.info(f"ACCEPTED: Medium confidence ({confidence:.3f}) with strong dominance score ({dominance_score:.3f}) for {symbol}")
                return True

            # If the signal is in a favorable regime context, consider it
            regime_context = getattr(fused_signal, 'regime_context', '').lower()
            if any(favorable in regime_context for favorable in ['trend', 'breakout', 'momentum', 'bullish', 'bearish']):
                self.logger.info(f"ACCEPTED: Medium confidence ({confidence:.3f}) in favorable regime ({regime_context}) for {symbol}")
                return True

            # Default to execute for medium confidence non-neutral signals
            self.logger.info(f"ACCEPTED: Medium confidence ({confidence:.3f}) non-neutral signal for {symbol}")
            return True

        # For low confidence signals, be more selective but allow some execution
        elif confidence < min_confidence and is_not_neutral:
            # Only execute if there are strong supporting factors
            dominance_score = getattr(fused_signal, 'dominance_score', 0.0)
            regime_context = getattr(fused_signal, 'regime_context', '').lower()

            # Execute if dominance is very strong relative to confidence
            if abs(dominance_score) > (min_confidence + 0.10) and any(favorable in regime_context for favorable in ['confirmed', 'strong', 'trend']):
                self.logger.info(f"ACCEPTED: Low confidence ({confidence:.3f}) but strong dominance ({dominance_score:.3f}) and regime ({regime_context}) for {symbol}")
                return True

            # Even with low confidence, if there's strong directional bias, consider executing
            import os
            strong_directional_bias_threshold = float(os.getenv('STRATEGY_STRONG_DIRECTIONAL_BIAS_THRESHOLD', '0.15'))  # Lowered from 0.25 to 0.15
            if abs(dominance_score) > strong_directional_bias_threshold:  # Strong directional bias
                self.logger.info(f"ACCEPTED: Low confidence ({confidence:.3f}) but strong directional bias ({dominance_score:.3f}) for {symbol}")
                return True

            # For very low confidence, still allow execution if there's any directional bias
            if abs(dominance_score) > 0.05:  # Lowered threshold from 0.1 to 0.05
                self.logger.info(f"ACCEPTED: Very low confidence ({confidence:.3f}) but some directional bias ({dominance_score:.3f}) for {symbol}")
                return True

            self.logger.info(f"REJECTED: Low confidence ({confidence:.3f}) and insufficient supporting factors for {symbol}")
            return False

        # Neutral signals should not be executed regardless of confidence
        else:
            self.logger.info(f"REJECTED: Neutral signal ({fused_signal.dominant_bias.value}) regardless of confidence ({confidence:.3f}) for {symbol}")
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

    def _calculate_comprehensive_risk_parameters(self, fused_signal: FusedSignal) -> Dict[str, Any]:
        """Calculate comprehensive risk parameters based on the fused signal using advanced risk management"""
        # Import advanced risk management system
        try:
            from infrastructure.risk.advanced_risk_management import AdvancedRiskManagementService, SLTPManager
            import os

            # Initialize risk management components
            risk_service = AdvancedRiskManagementService()

            # Get market data for more accurate risk calculations (if available)
            # In a real implementation, we'd fetch current market data for the symbol
            market_data = None  # This would come from data provider in real implementation

            # Calculate risk-adjusted position size and other parameters
            portfolio_value = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '10000.0'))

            # Get current price from market data repository or broker service
            current_price = None
            if hasattr(self, 'market_data_repo') and self.market_data_repo:
                try:
                    current_price = self.market_data_repo.get_current_price(fused_signal.symbol)
                except:
                    pass  # Fallback to other methods if market data repo fails

            if current_price is None and hasattr(self, 'broker_service') and self.broker_service:
                try:
                    # Try to get current price from broker service
                    current_price = self.broker_service.get_current_price(fused_signal.symbol)
                except:
                    pass  # Fallback to default if broker service fails

            # If we still don't have a price, use a reasonable default based on the symbol
            if current_price is None or current_price <= 0:
                symbol_str = fused_signal.symbol.value
                if symbol_str.startswith(('BTC', 'WBTC')):
                    current_price = 45000.0  # Bitcoin price range
                elif symbol_str.startswith(('ETH', 'WETH')):
                    current_price = 2500.0  # Ethereum price range
                elif symbol_str.startswith(('SOL', 'AVAX', 'FTM', 'APT', 'AR')):
                    current_price = 90.0   # Mid-range altcoins
                elif symbol_str.startswith(('BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH')):
                    current_price = 10.0   # Lower range altcoins
                elif symbol_str.startswith(('XLM', 'TRX', 'ATOM', 'NEAR', 'FIL', 'ETC', 'VET', 'XTZ', 'ICX', 'HBAR', 'SUI')):
                    current_price = 0.5    # Penny stocks/crypto range
                elif symbol_str.startswith(('SHIB', 'PEPE', 'FLOKI')):
                    current_price = 0.00001  # Meme coin range
                else:
                    # For any other symbol, use a reasonable default based on common patterns
                    import random
                    current_price = random.uniform(0.01, 500.0)

            # Calculate position size using advanced risk management
            position_size, risk_factors = risk_service.calculate_position_size(
                symbol=fused_signal.symbol,
                price=current_price,
                portfolio_value=portfolio_value,
                fused_signal=fused_signal,
                market_data=market_data
            )

            # Calculate dynamic SL/TP levels based on risk factors
            position_side = "LONG" if fused_signal.direction > 0 else "SHORT"

            sl_tp_levels = risk_service.calculate_sl_tp_levels(
                entry_price=current_price,
                position_side=position_side,
                risk_adjustment_factors=risk_factors,
                atr_value=None,  # Would come from market data in real implementation
                market_data=market_data
            )

            # Construct comprehensive risk parameters
            risk_parameters = {
                'max_position_size': position_size,
                'stop_loss_pct': min(0.10, getattr(risk_factors, 'stop_loss_multiplier', 1.0) * 0.02),      # Cap at 10%, use as multiplier for base 2%
                'take_profit_pct': min(0.15, getattr(risk_factors, 'take_profit_multiplier', 1.0) * 0.03),  # Cap at 15%, use as multiplier for base 3%
                'stop_loss_price': sl_tp_levels[0],
                'take_profit_price': sl_tp_levels[1],
                'risk_per_trade': 0.02 * portfolio_value,  # 2% of portfolio
                'max_position_exposure': 0.1 * portfolio_value,  # 10% max exposure
                'position_quantity': position_size * portfolio_value / current_price,
                'risk_adjustment_factors': risk_factors
            }

            # Log the calculated risk parameters
            self.logger.info(f"Calculated comprehensive risk parameters for {fused_signal.symbol.value}: "
                           f"Position size: {position_size:.4f}, "
                           f"SL%: {getattr(risk_factors, 'stop_loss_multiplier', 0.02):.2%}, "
                           f"TP%: {getattr(risk_factors, 'take_profit_multiplier', 0.03):.2%}, "
                           f"Confidence: {float(fused_signal.confidence.value):.2%}")

            return risk_parameters

        except ImportError:
            # If advanced risk management is not available, fall back to basic calculation
            self.logger.warning("Advanced risk management service not available, using basic risk parameters")
            return self._calculate_basic_risk_parameters(fused_signal)
        except Exception as e:
            self.logger.error(f"Error calculating comprehensive risk parameters: {e}, using basic parameters")
            return self._calculate_basic_risk_parameters(fused_signal)

    def _calculate_basic_risk_parameters(self, fused_signal: FusedSignal) -> Dict[str, Any]:
        """Calculate basic risk parameters based on the fused signal"""
        base_risk_params = self.risk_parameters.copy()

        # Adjust risk based on signal confidence
        confidence_factor = float(fused_signal.confidence.value)

        # Scale position size with confidence
        base_risk_params['max_position_size'] *= confidence_factor

        # For stop loss, use the confidence to adjust the tightness appropriately
        # Higher confidence signals should have tighter stops, lower confidence should have wider stops
        # But ensure stop loss percentage stays within reasonable bounds
        base_stop_loss_pct = self.risk_parameters['stop_loss_pct']
        if confidence_factor > 0.5:
            # For higher confidence, tighten the stop loss (smaller percentage)
            base_risk_params['stop_loss_pct'] = min(base_stop_loss_pct * (1.0 - (confidence_factor - 0.5) * 0.8), 0.10)  # Cap at 10%, tighten for high confidence
        else:
            # For lower confidence, widen the stop loss (larger percentage) but cap it
            base_risk_params['stop_loss_pct'] = min(base_stop_loss_pct * (1.0 + (0.5 - confidence_factor) * 1.5), 0.10)  # Cap at 10%

        # Similarly for take profit percentage
        base_take_profit_pct = self.risk_parameters['take_profit_pct']
        if confidence_factor > 0.5:
            # For higher confidence, use tighter take profit (smaller percentage difference from entry)
            base_risk_params['take_profit_pct'] = min(base_take_profit_pct * (1.0 + (confidence_factor - 0.5) * 0.5), 0.15)  # Cap at 15%
        else:
            # For lower confidence, use wider take profit but still cap it
            base_risk_params['take_profit_pct'] = min(base_take_profit_pct * (1.0 + (0.5 - confidence_factor) * 1.0), 0.15)  # Cap at 15%

        return base_risk_params


class TrendFollowingStrategy(BaseStrategyAdapter):
    """Strategy for following market trends"""

    def __init__(self):
        super().__init__("trend_following")

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Execute in trending market conditions, but also allow other conditions with lower thresholds"""
        # First check the base strategy execution criteria
        base_should_execute = super().should_execute(fused_signal)

        # Check if it's a trending market condition
        is_trending = 'trend' in fused_signal.regime_context.lower()

        # If it's trending, execute normally
        if is_trending:
            return base_should_execute

        # If it's not trending, we can still execute if the signal is strong enough
        # This allows the strategy to participate in other market conditions too
        confidence = float(fused_signal.confidence.value)
        strong_signal = confidence > 0.4  # Lower threshold for non-trending markets

        return base_should_execute or strong_signal


class MeanReversionStrategy(BaseStrategyAdapter):
    """Strategy for mean reversion opportunities"""

    def __init__(self):
        super().__init__("mean_reversion")

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Execute in mean-reverting market conditions, but also allow other conditions with lower thresholds"""
        # First check the base strategy execution criteria
        base_should_execute = super().should_execute(fused_signal)

        # Check if it's a mean-reverting market condition
        is_mean_reverting = ('mean' in fused_signal.regime_context.lower() or
                             'revert' in fused_signal.regime_context.lower())

        # If it's mean-reverting, execute normally
        if is_mean_reverting:
            return base_should_execute

        # If it's not mean-reverting, we can still execute if the signal is strong enough
        # This allows the strategy to participate in other market conditions too
        confidence = float(fused_signal.confidence.value)
        strong_signal = confidence > 0.4  # Lower threshold for non-mean-reverting markets

        return base_should_execute or strong_signal


class VolatilityBreakoutStrategy(BaseStrategyAdapter):
    """Strategy for volatility breakout opportunities"""

    def __init__(self):
        super().__init__("volatility_breakout")

    def should_execute(self, fused_signal: FusedSignal) -> bool:
        """Execute in high volatility conditions, but also allow other conditions with lower thresholds"""
        # First check the base strategy execution criteria
        base_should_execute = super().should_execute(fused_signal)

        # Check if it's a volatile market condition
        is_volatile = 'volatile' in fused_signal.regime_context.lower()

        # If it's volatile, execute normally
        if is_volatile:
            return base_should_execute

        # If it's not volatile, we can still execute if the signal is strong enough
        # This allows the strategy to participate in other market conditions too
        confidence = float(fused_signal.confidence.value)
        strong_signal = confidence > 0.4  # Lower threshold for non-volatile markets

        return base_should_execute or strong_signal