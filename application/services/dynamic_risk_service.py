"""
Enhanced dynamic risk adjustment service for the enterprise hedge fund trading system.
This service provides more dynamic risk adjustment mechanisms that adapt to market conditions.
"""
from typing import Dict, List, Optional, Any
import numpy as np
from datetime import datetime, timedelta
from domain.entities import Signal, Order, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.engine_ports import RiskGovernorPort
from domain.ports.trading_ports import RiskManagementPort
from application.services.risk_services_app import RiskGovernanceService
from shared.logger import logger


class DynamicRiskAdjustmentService:
    """Service for dynamic risk adjustments based on market conditions and portfolio metrics"""

    def __init__(self, risk_governor: RiskGovernorPort, risk_management: RiskManagementPort):
        self.risk_governor = risk_governor
        self.risk_management = risk_management
        
        # Dynamic risk parameters that adapt to market conditions
        self.dynamic_parameters = {
            'volatility_multiplier': 1.0,
            'correlation_adjustment': 1.0,
            'drawdown_recovery_mode': False,
            'trend_adjustment': 1.0,
            'time_decay_factor': 1.0
        }
        
        # Historical risk metrics for adaptation
        self.risk_history = {
            'volatility_buffer': [],
            'correlation_buffer': [],
            'drawdown_history': [],
            'position_size_history': [],
            'recent_losses': [],
            'market_regime_history': []
        }
        
        # Risk thresholds that can be dynamically adjusted
        self.risk_thresholds = {
            'max_position_size': Percentage(0.02),  # Max 2% per position
            'max_portfolio_drawdown': Percentage(0.15),  # Max 15% portfolio drawdown
            'max_correlation_threshold': 0.7,  # Max 70% correlation with other positions
            'volatility_threshold_low': 0.01,  # Low volatility threshold
            'volatility_threshold_high': 0.03,  # High volatility threshold
            'max_daily_loss': Percentage(0.05),  # Max 5% daily loss
            'max_leverage': 5.0  # Max 5x leverage
        }

    def update_risk_parameters(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Update risk parameters based on current market conditions"""
        # Calculate dynamic adjustments based on market data
        volatility_multiplier = self._calculate_volatility_multiplier(market_data)
        correlation_adjustment = self._calculate_correlation_adjustment(market_data)
        trend_adjustment = self._calculate_trend_adjustment(market_data)
        time_decay_factor = self._calculate_time_decay_factor()
        
        # Update dynamic parameters
        self.dynamic_parameters.update({
            'volatility_multiplier': volatility_multiplier,
            'correlation_adjustment': correlation_adjustment,
            'trend_adjustment': trend_adjustment,
            'time_decay_factor': time_decay_factor
        })
        
        # Check for drawdown recovery mode
        current_drawdown = self._get_current_drawdown()
        self.dynamic_parameters['drawdown_recovery_mode'] = current_drawdown < -0.05  # More conservative after 5% drawdown
        
        logger.info(f"Updated dynamic risk parameters: {self.dynamic_parameters}")
        return self.dynamic_parameters

    def adjust_signal_for_risk(self, signal: Signal) -> Signal:
        """Adjust a signal based on dynamic risk parameters"""
        # Store original signal values
        original_confidence = float(signal.confidence.value)
        original_score = signal.score
        
        # Calculate risk adjustments
        volatility_adjustment = self.dynamic_parameters.get('volatility_multiplier', 1.0)
        correlation_adjustment = self.dynamic_parameters.get('correlation_adjustment', 1.0)
        trend_adjustment = self.dynamic_parameters.get('trend_adjustment', 1.0)
        time_decay = self.dynamic_parameters.get('time_decay_factor', 1.0)
        
        # Apply adjustments based on risk mode
        if self.dynamic_parameters.get('drawdown_recovery_mode', False):
            # Be more conservative after significant drawdowns
            combined_adjustment = min(0.8, volatility_adjustment * correlation_adjustment * trend_adjustment)
        else:
            # Normal risk adjustments
            combined_adjustment = volatility_adjustment * correlation_adjustment * trend_adjustment * time_decay
        
        # Calculate new confidence score
        new_confidence = min(1.0, max(0.1, original_confidence * combined_adjustment))
        
        # Calculate new score based on risk-adjusted parameters
        new_score = original_score * combined_adjustment
        
        # Create adjusted signal with new risk parameters
        adjusted_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=Percentage(str(new_confidence)),
            score=new_score,
            strategy_name=f"{signal.strategy_name}_risk_adjusted",
            timestamp=signal.timestamp,
            source_engine=signal.source_engine,
            metadata={
                **(signal.metadata or {}),
                'original_confidence': original_confidence,
                'risk_adjustment_factor': combined_adjustment,
                'volatility_multiplier': volatility_adjustment,
                'correlation_adjustment': correlation_adjustment,
                'trend_adjustment': trend_adjustment,
                'drawdown_recovery_mode': self.dynamic_parameters.get('drawdown_recovery_mode', False),
                'risk_adjusted': True
            }
        )
        
        logger.info(f"Adjusted signal risk: {signal.signal_type.name}, "
                   f"confidence {original_confidence:.2%} -> {new_confidence:.2%}, "
                   f"factor: {combined_adjustment:.2f}")
        
        return adjusted_signal

    def adjust_order_for_risk(self, order: Order) -> Order:
        """Adjust an order based on dynamic risk parameters"""
        # Calculate position size based on risk parameters
        risk_adjusted_size = self.calculate_risk_adjusted_position_size(
            order.symbol, 
            order.quantity, 
            order.price.amount
        )
        
        # Update order with risk-adjusted size
        risk_adjusted_order = Order(
            symbol=order.symbol,
            side=order.side,
            quantity=risk_adjusted_size,
            price=order.price,
            order_type=order.order_type,
            strategy=order.strategy,
            timestamp=order.timestamp,
            metadata={
                **(order.metadata or {}),
                'original_quantity': order.quantity,
                'risk_adjustment_applied': True,
                'risk_adjustment_factor': risk_adjusted_size / order.quantity if order.quantity > 0 else 1.0
            }
        )
        
        return risk_adjusted_order

    def calculate_risk_adjusted_position_size(self, symbol: Symbol, requested_size: float, price: float) -> float:
        """Calculate position size based on dynamic risk parameters"""
        # Start with requested size
        position_size = requested_size
        
        # Apply volatility-based adjustment
        volatility_multiplier = self.dynamic_parameters.get('volatility_multiplier', 1.0)
        position_size *= min(1.0, 1.0 / volatility_multiplier)  # Lower size when volatility is high
        
        # Apply correlation-based adjustment to avoid over-allocation to similar strategies
        correlation_adjustment = self.dynamic_parameters.get('correlation_adjustment', 1.0)
        position_size *= correlation_adjustment
        
        # Apply trend-based adjustment if we're in a risky market trend
        trend_adjustment = self.dynamic_parameters.get('trend_adjustment', 1.0)
        if trend_adjustment < 0.8:  # If trend suggests increased risk
            position_size *= trend_adjustment
        
        # Apply drawdown recovery mode if applicable
        if self.dynamic_parameters.get('drawdown_recovery_mode', False):
            position_size *= 0.7  # Reduce position size by 30% in recovery mode
        
        # Ensure position doesn't exceed max allocation for the symbol
        max_allocation = self._calculate_max_allocation_for_symbol(symbol)
        portfolio_value = self._get_portfolio_value()
        max_position_size = (portfolio_value * float(self.risk_thresholds['max_position_size'].value)) / price
        
        # Limit to the minimum of risk-adjusted size and max allowed size
        position_size = min(position_size, max_position_size)
        
        # Add to history for future reference
        self._add_to_position_history(position_size)
        
        return position_size

    def validate_order_with_dynamic_risk(self, order: Order) -> bool:
        """Validate an order using dynamic risk checks"""
        # Check current portfolio exposure
        if self.risk_management.is_risk_limit_exceeded():
            logger.warning(f"Order {order.symbol.value} rejected: Risk limits exceeded")
            return False

        # Calculate and apply dynamic risk adjustments
        risk_adjusted_order = self.adjust_order_for_risk(order)
        
        # Check if the adjusted size is still within acceptable thresholds
        max_position_size = self.risk_governor.get_max_position_size(order.symbol)
        if risk_adjusted_order.quantity > max_position_size:
            logger.warning(f"Order {order.symbol.value} quantity {risk_adjusted_order.quantity} exceeds "
                          f"max allowed {max_position_size}")
            return False

        # Additional checks based on market conditions
        market_volatility = self._get_current_market_volatility(order.symbol)
        if market_volatility > self.risk_thresholds['volatility_threshold_high']:
            # In high volatility conditions, be more conservative
            if risk_adjusted_order.quantity > max_position_size * 0.5:
                logger.warning(f"High volatility detected for {order.symbol.value}, reducing position size")
                return False

        return True

    def _calculate_volatility_multiplier(self, market_data: Dict[str, Any]) -> float:
        """Calculate volatility-based risk multiplier"""
        volatility = market_data.get('volatility', 0.02)  # Default to 2% if not provided
        
        # Adjust multiplier based on volatility levels
        if volatility > self.risk_thresholds['volatility_threshold_high']:
            # High volatility - reduce risk exposure
            return max(0.3, 1.0 - (volatility - self.risk_thresholds['volatility_threshold_high']))
        elif volatility < self.risk_thresholds['volatility_threshold_low']:
            # Low volatility - can take more risk
            return min(1.3, 1.0 + (self.risk_thresholds['volatility_threshold_low'] - volatility) * 2)
        else:
            # Normal volatility - standard risk level
            return 1.0

    def _calculate_correlation_adjustment(self, market_data: Dict[str, Any]) -> float:
        """Calculate correlation-based risk adjustment"""
        # This would typically check correlation with other positions in portfolio
        # For now, we'll return a basic adjustment based on market regime
        market_regime = market_data.get('regime', 'normal')
        
        if market_regime == 'high_correlation':
            # In high correlation environments, reduce risk
            return 0.7
        elif market_regime == 'low_correlation':
            # In diversified environments, can take more risk
            return 1.1
        else:
            # Normal conditions
            return 1.0

    def _calculate_trend_adjustment(self, market_data: Dict[str, Any]) -> float:
        """Calculate trend-based risk adjustment"""
        trend_strength = market_data.get('trend_strength', 0.0)
        trend_direction = market_data.get('trend_direction', 0)  # -1 for downtrend, 1 for uptrend
        
        # If we're in a strong downtrend, be more conservative
        if trend_direction < 0 and abs(trend_strength) > 0.3:
            return 0.8
        # If we're in a strong uptrend, can be more aggressive
        elif trend_direction > 0 and trend_strength > 0.3:
            return 1.1
        else:
            # Neutral trend
            return 1.0

    def _calculate_time_decay_factor(self) -> float:
        """Calculate time-based decay factor for risk adjustments"""
        # This could implement time decay based on recent performance
        # For example, reducing risk after a series of losses
        recent_losses = self.risk_history.get('recent_losses', [])
        
        if len(recent_losses) >= 3:
            avg_loss = sum(recent_losses[-3:]) / 3
            if avg_loss > 0:  # If we had recent losses
                return max(0.7, 1.0 - (avg_loss * 0.5))  # Be more conservative after losses
        
        return 1.0

    def _get_current_drawdown(self) -> float:
        """Get current portfolio drawdown"""
        # This would connect to the actual risk management system
        # For now, we'll return a simulated value
        return -0.02  # -2% drawdown as an example

    def _get_current_market_volatility(self, symbol: Symbol) -> float:
        """Get current market volatility for a symbol"""
        # This would connect to market data feeds
        # For now, returning a simulated value
        return 0.015  # 1.5% daily volatility

    def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        # This would connect to portfolio management
        # Return a simulated value
        return 1000000.0  # $1M portfolio

    def _calculate_max_allocation_for_symbol(self, symbol: Symbol) -> float:
        """Calculate max allowed allocation for a specific symbol"""
        # This would implement symbol-specific risk limits
        return 0.05  # 5% max allocation per symbol

    def _add_to_position_history(self, position_size: float):
        """Add position size to history for trend analysis"""
        self.risk_history['position_size_history'].append({
            'timestamp': datetime.now(),
            'size': position_size
        })
        
        # Keep only last 100 entries
        if len(self.risk_history['position_size_history']) > 100:
            self.risk_history['position_size_history'] = self.risk_history['position_size_history'][-100:]

    def get_dynamic_risk_metrics(self) -> Dict[str, Any]:
        """Get current dynamic risk metrics and parameters"""
        return {
            'dynamic_parameters': self.dynamic_parameters.copy(),
            'risk_thresholds': self.risk_thresholds.copy(),
            'position_history_count': len(self.risk_history['position_size_history']),
            'recent_losses_count': len(self.risk_history['recent_losses']),
            'portfolio_drawdown': self._get_current_drawdown(),
            'last_updated': datetime.now().isoformat()
        }

    def reset_risk_state(self):
        """Reset risk state when leaving drawdown recovery mode or other special modes"""
        self.dynamic_parameters['drawdown_recovery_mode'] = False
        # Reset other special state parameters as needed