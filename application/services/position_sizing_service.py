"""
Enhanced position sizing service with multiple advanced position sizing algorithms
for the enterprise hedge fund trading system.
"""
import math
import os
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import numpy as np
import pandas as pd
from domain.entities.trading_entities import Signal, Order, Position
from domain.value_objects import Symbol, Money, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger


class EnhancedPositionSizingService:
    """Service for calculating position sizes using multiple advanced algorithms"""

    def __init__(self):
        # Configuration for different sizing algorithms using environment variables
        self.kelly_config = {
            'max_position_size': float(os.getenv('KELLY_MAX_POSITION_SIZE', '0.10')),  # Maximum percentage per position
            'kelly_fraction': float(os.getenv('KELLY_FRACTION', '0.25')),  # Use fraction of full Kelly recommendation
            'minimum_edge': float(os.getenv('KELLY_MINIMUM_EDGE', '0.01')),  # Minimum edge required to trade
            'maximum_drawdown_threshold': float(os.getenv('MAX_DRAWDOWN_THRESHOLD', '0.15'))  # Max portfolio drawdown
        }

        self.fixed_fractional_config = {
            'percentage_per_trade': float(os.getenv('FIXED_FRACTIONAL_PERCENTAGE', '0.02')),  # Risk % of portfolio per trade
            'risk_per_unit': float(os.getenv('FIXED_FRACTIONAL_RISK_PER_UNIT', '0.01')),  # Risk per unit of position
            'minimum_position_size': float(os.getenv('MIN_POSITION_SIZE', '100')),  # Minimum trade size in USD
            'maximum_position_size': float(os.getenv('MAX_POSITION_SIZE', '50000'))  # Maximum trade size in USD
        }

        self.atr_based_config = {
            'atr_multiplier': float(os.getenv('ATR_MULTIPLIER', '2.0')),  # ATR multiple for stop distance
            'fixed_dollar_risk': float(os.getenv('ATR_FIXED_DOLLAR_RISK', '1000')),  # Dollar risk per trade maximum
            'minimum_atr_multiple': float(os.getenv('ATR_MIN_MULTIPLE', '1.5')),  # Minimum ATR multiple for position size
        }

        self.correlation_adjusted_config = {
            'maximum_correlation': float(os.getenv('CORRELATION_MAX_CORRELATION', '0.7')),  # Max correlation with portfolio
            'diversification_factor': float(os.getenv('CORRELATION_DIVERSIFICATION_FACTOR', '0.85')),  # Reduce as correlation increases
            'portfolio_impact_threshold': float(os.getenv('CORRELATION_PORTFOLIO_IMPACT_THRESHOLD', '0.05'))  # Max portfolio impact per position
        }

        # Additional configurations for other algorithms
        self.optimal_f_config = {
            'maximum_f_per_trade': float(os.getenv('OPTIMAL_F_MAX_PER_TRADE', '0.25')),  # Max 25% per trade
            'default_percentage_when_insufficient_data': float(os.getenv('OPTIMAL_F_DEFAULT_PERCENTAGE', '0.05')),  # Default 5% if insufficient data
            'calculation_error_fallback_percentage': float(os.getenv('OPTIMAL_F_ERROR_FALLBACK_PERCENTAGE', '0.02'))  # Default 2% if calculation fails
        }

        self.volatility_targeted_config = {
            'target_volatility_percentage': float(os.getenv('VOLATILITY_TARGET_PERCENTAGE', '0.15')),  # Target 15% annual volatility
            'maximum_portfolio_allocation': float(os.getenv('VOLATILITY_MAX_PORTFOLIO_ALLOCATION', '0.15')),  # Max 15% of portfolio
            'calculation_error_default': float(os.getenv('VOLATILITY_ERROR_DEFAULT_PERCENTAGE', '0.01'))  # Default 1% if calculation fails
        }

        self.martingale_config = {
            'base_risk_percentage': float(os.getenv('MARTINGALE_BASE_RISK_PERCENTAGE', '0.01')),  # Base 1% risk
            'maximum_progression_levels': int(os.getenv('MARTINGALE_MAX_PROGRESSION_LEVELS', '5')),  # Max 5 levels
            'progression_multiplier': float(os.getenv('MARTINGALE_PROGRESSION_MULTIPLIER', '2.0'))  # 2x progression
            'maximum_total_exposure_multiplier': float(os.getenv('MARTINGALE_MAX_TOTAL_EXPOSURE_MULTIPLIER', '10.0'))  # Max 10x total exposure
        }

        self.kelly_var_config = {
            'var_confidence_level': float(os.getenv('KELLY_VAR_CONFIDENCE_LEVEL', '0.95')),  # 95% confidence for VaR
            'maximum_position_with_var': float(os.getenv('KELLY_VAR_MAX_POSITION_WITH_VAR', '0.10')),  # Max 10% with VaR controls
            'stress_test_multiplier': float(os.getenv('KELLY_VAR_STRESS_TEST_MULTIPLIER', '1.5')),  # Stress test factor
            'margin_of_safety_percentage': float(os.getenv('KELLY_VAR_MARGIN_OF_SAFETY_PERCENTAGE', '0.20'))  # 20% margin of safety
        }

    def calculate_position_size(self, 
                                signal: Signal, 
                                portfolio_value: float, 
                                algorithm: str = 'kelly',
                                market_data: Optional[Dict[str, Any]] = None) -> float:
        """Calculate position size using specified algorithm"""
        
        if algorithm.lower() == 'kelly':
            return self._calculate_kelly_position_size(signal, portfolio_value, market_data)
        elif algorithm.lower() == 'fixed_fractional':
            return self._calculate_fixed_fractional_position_size(signal, portfolio_value, market_data)
        elif algorithm.lower() == 'atr_based':
            return self._calculate_atr_based_position_size(signal, portfolio_value, market_data)
        elif algorithm.lower() == 'correlation_adjusted':
            return self._calculate_correlation_adjusted_position_size(signal, portfolio_value, market_data)
        elif algorithm.lower() == 'optimal_f':
            return self._calculate_optimal_f_position_size(signal, portfolio_value, market_data)
        elif algorithm.lower() == 'volatility_targeted':
            return self._calculate_volatility_targeted_position_size(signal, portfolio_value, market_data)
        else:
            # Default to Kelly if unknown algorithm
            logger.warning(f"Unknown algorithm '{algorithm}', using Kelly criterion")
            return self._calculate_kelly_position_size(signal, portfolio_value, market_data)

    def _calculate_kelly_position_size(self, signal: Signal, portfolio_value: float, market_data: Optional[Dict[str, Any]]) -> float:
        """Calculate position size using Kelly Criterion"""
        try:
            # Get edge and odds from the signal and market data
            edge = self._estimate_edge(signal, market_data)
            win_rate = self._estimate_win_rate(signal, market_data)

            # Estimate reward:risk ratio
            reward_risk_ratio = self._estimate_reward_risk_ratio(signal, market_data)

            if edge < self.kelly_config['minimum_edge']:
                logger.info(f"Kelly: Insufficient edge ({edge:.3f} < {self.kelly_config['minimum_edge']:.3f}), not trading")
                return 0.0

            # Kelly formula: position_size = (bp - q)/b
            # where b = reward:risk ratio, p = win rate, q = 1-p
            winning_probability = win_rate
            losing_probability = 1 - win_rate

            # Adjust for reward: risk ratio
            kelly_fraction = ((reward_risk_ratio * winning_probability) - losing_probability) / reward_risk_ratio

            # Limit position size to maximum allowed
            kelly_fraction = min(kelly_fraction, self.kelly_config['max_position_size'])

            # Use fraction of Kelly recommendation to reduce volatility
            position_fraction = kelly_fraction * self.kelly_config['kelly_fraction']

            # Calculate position size in dollars
            position_size = portfolio_value * max(0, position_fraction)  # Ensure no negative positions

            logger.info(f"Kelly: Edge={edge:.3f}, WinRate={win_rate:.3f}, RR={reward_risk_ratio:.2f}, Size=${position_size:,.2f}")
            return position_size

        except Exception as e:
            logger.error(f"Error in Kelly position sizing: {e}")
            # Use configurable default percentage
            default_percentage = float(os.getenv('KELLY_DEFAULT_PERCENTAGE', '0.01'))
            return portfolio_value * default_percentage  # Default to configurable % if calculation fails

    def _calculate_fixed_fractional_position_size(self, signal: Signal, portfolio_value: float, market_data: Optional[Dict[str, Any]]) -> float:
        """Calculate position size using fixed fractional method"""
        try:
            # Use a fixed percentage of portfolio per trade
            position_size = portfolio_value * self.fixed_fractional_config['percentage_per_trade']

            # Apply minimum and maximum position size limits
            position_size = max(position_size, self.fixed_fractional_config['minimum_position_size'])
            position_size = min(position_size, self.fixed_fractional_config['maximum_position_size'])

            logger.info(f"Fixed Fractional: {self.fixed_fractional_config['percentage_per_trade']:.1%} of portfolio = ${position_size:,.2f}")
            return position_size

        except Exception as e:
            logger.error(f"Error in Fixed Fractional position sizing: {e}")
            # Use configurable default percentage
            default_percentage = float(os.getenv('FIXED_FRACTIONAL_DEFAULT_PERCENTAGE', '0.02'))
            return portfolio_value * default_percentage  # Default to configurable % if calculation fails

    def _calculate_atr_based_position_size(self, signal: Signal, portfolio_value: float, market_data: Optional[Dict[str, Any]]) -> float:
        """Calculate position size using ATR-based position sizing"""
        try:
            if not market_data or 'atr' not in market_data or 'price' not in market_data:
                logger.warning("ATR-based sizing requires ATR and price data, using Kelly instead")
                return self._calculate_kelly_position_size(signal, portfolio_value, market_data)

            atr = market_data['atr']
            price = market_data['price']

            # Calculate stop distance based on ATR
            stop_distance = atr * self.atr_based_config['atr_multiplier']

            # Calculate risk per share/unit
            risk_per_unit = stop_distance

            # Calculate position size based on fixed dollar risk
            position_size = self.atr_based_config['fixed_dollar_risk'] / risk_per_unit

            # Convert to dollar amount
            dollar_position = position_size * price

            # Apply maximum position size limit from environment (default 10% of portfolio)
            max_portfolio_percent = float(os.getenv('ATR_MAX_PORTFOLIO_PERCENT', '0.10'))
            max_position = portfolio_value * max_portfolio_percent
            dollar_position = min(dollar_position, max_position)

            logger.info(f"ATR-Based: Price=${price:.2f}, ATR=${atr:.2f}, Stop=${stop_distance:.2f}, Size=${dollar_position:,.2f}")
            return dollar_position

        except Exception as e:
            logger.error(f"Error in ATR-based position sizing: {e}")
            return portfolio_value * float(os.getenv('ATR_DEFAULT_PERCENTAGE', '0.015'))  # Default configurable percentage

    def _calculate_correlation_adjusted_position_size(self, signal: Signal, portfolio_value: float, market_data: Optional[Dict[str, Any]]) -> float:
        """Calculate position size based on correlation with existing positions"""
        try:
            # Start with a base position size from environment variable (default 2% of portfolio)
            base_percentage = float(os.getenv('CORRELATION_BASE_PERCENTAGE', '0.02'))
            base_position = portfolio_value * base_percentage

            # Get portfolio correlation information if available
            correlation_factor = 1.0
            if market_data and 'portfolio_correlation' in market_data:
                portfolio_correlation = market_data['portfolio_correlation']

                # Reduce position size as correlation increases
                if portfolio_correlation > self.correlation_adjusted_config['maximum_correlation']:
                    reduction_factor = 1 - (
                        (portfolio_correlation - self.correlation_adjusted_config['maximum_correlation']) *
                        (1.0 / (1.0 - self.correlation_adjusted_config['maximum_correlation'])) *
                        (1.0 - self.correlation_adjusted_config['diversification_factor'])
                    )
                    correlation_factor = max(self.correlation_adjusted_config['diversification_factor'], reduction_factor)

            # Calculate final position size
            position_size = base_position * correlation_factor

            logger.info(f"Correlation Adjusted: Base=${base_position:,.2f}, Factor={correlation_factor:.2f}, Size=${position_size:,.2f}")
            return position_size

        except Exception as e:
            logger.error(f"Error in Correlation Adjusted position sizing: {e}")
            # Use configurable default percentage
            default_percentage = float(os.getenv('CORRELATION_DEFAULT_PERCENTAGE', '0.02'))
            return portfolio_value * default_percentage  # Default to configurable % if calculation fails

    def _calculate_optimal_f_position_size(self, signal: Signal, portfolio_value: float, market_data: Optional[Dict[str, Any]]) -> float:
        """Calculate position size using Ralph Vince's Optimal F method"""
        try:
            # Optimal F is calculated as the optimal fraction of account to risk per trade
            # For simplicity, we'll estimate based on win rate and reward ratio

            win_rate = self._estimate_win_rate(signal, market_data)
            reward_risk_ratio = self._estimate_reward_risk_ratio(signal, market_data)

            # Simplified calculation of Optimal F
            # In practice, this would use historical trade data
            if win_rate > 0.5 and reward_risk_ratio > 0:
                # Approximation of optimal f: f = ((b+1)*p - 1) / b
                # where b is win/loss ratio and p is win probability
                approximate_f = ((reward_risk_ratio + 1) * win_rate - 1) / reward_risk_ratio
                # Cap at configurable value (default 25% per trade)
                max_f_per_trade = float(os.getenv('OPTIMAL_F_MAX_PER_TRADE', '0.25'))
                f_to_use = max(0, min(approximate_f, max_f_per_trade))
            else:
                # Default to configurable percentage if calculations fail
                f_to_use = float(os.getenv('OPTIMAL_F_DEFAULT_PERCENTAGE', '0.05'))

            position_size = portfolio_value * f_to_use

            logger.info(f"Optimal F: Estimated F={f_to_use:.3f}, WinRate={win_rate:.3f}, RR={reward_risk_ratio:.2f}, Size=${position_size:,.2f}")
            return position_size

        except Exception as e:
            logger.error(f"Error in Optimal F position sizing: {e}")
            # Use configurable default percentage
            default_percentage = float(os.getenv('OPTIMAL_F_CALCULATION_ERROR_DEFAULT', '0.02'))
            return portfolio_value * default_percentage  # Default to configurable % if calculation fails

    def _calculate_volatility_targeted_position_size(self, signal: Signal, portfolio_value: float, market_data: Optional[Dict[str, Any]]) -> float:
        """Calculate position size to achieve a target volatility"""
        try:
            # Target volatility approach - adjust position size based on asset volatility
            # to achieve consistent portfolio volatility

            target_volatility = float(os.getenv('VOLATILITY_TARGET', '0.15'))  # Target 15% annual volatility from env
            max_portfolio_percent = float(os.getenv('VOLATILITY_MAX_PORTFOLIO_PERCENT', '0.15'))  # Max 15% of portfolio from env
            asset_volatility = self._estimate_asset_volatility(signal, market_data)

            if asset_volatility <= 0:
                logger.warning("Asset volatility estimate is invalid, using Kelly instead")
                return self._calculate_kelly_position_size(signal, portfolio_value, market_data)

            # Calculate position size to achieve target volatility
            # Position size = (target_vol * portfolio_value) / (asset_vol * price)
            position_size_ratio = target_volatility / asset_volatility
            position_size = portfolio_value * position_size_ratio * 0.1  # Scale appropriately

            # Apply maximum position size constraint
            max_position = portfolio_value * max_portfolio_percent  # Use configurable percentage
            position_size = min(position_size, max_position)

            logger.info(f"Volatility Targeted: AssetVol={asset_volatility:.3f}, Target={target_volatility:.3f}, Size=${position_size:,.2f}")
            return position_size

        except Exception as e:
            logger.error(f"Error in Volatility Targeted position sizing: {e}")
            return portfolio_value * 0.01  # Default to 1% if calculation fails

    def _estimate_edge(self, signal: Signal, market_data: Optional[Dict[str, Any]]) -> float:
        """Estimate the trading edge of the signal"""
        # Edge is the expected value of the trade
        # This is a simplified estimation using configurable parameters
        edge_factor = float(os.getenv('EDGE_ESTIMATION_FACTOR', '0.1'))
        base_edge = float(signal.confidence.value) * edge_factor  # Base on signal confidence with configurable factor

        # Adjust based on market conditions if available
        if market_data:
            default_volatility = float(os.getenv('DEFAULT_ASSET_VOLATILITY', '0.02'))
            max_volatility_impact = float(os.getenv('MAX_VOLATILITY_IMPACT_ON_EDGE', '0.2'))
            volatility_multiplier = float(os.getenv('VOLATILITY_IMPACT_MULTIPLIER', '2.0'))
            max_trend_impact = float(os.getenv('MAX_TREND_IMPACT_ON_EDGE', '0.5'))

            volatility = market_data.get('volatility', default_volatility)
            trend_strength = abs(market_data.get('trend_strength', 0.0))

            # Higher volatility may reduce edge (configurable impact)
            base_edge *= (1 - min(max_volatility_impact, volatility * volatility_multiplier))
            # Stronger trends may improve edge (configurable impact)
            base_edge *= (1 + min(max_trend_impact, trend_strength))

        return base_edge

    def _estimate_win_rate(self, signal: Signal, market_data: Optional[Dict[str, Any]]) -> float:
        """Estimate the win rate of the signal"""
        # Start with signal confidence as baseline
        base_win_rate = float(signal.confidence.value)

        # Adjust based on market conditions if available
        if market_data:
            high_vol_threshold = float(os.getenv('HIGH_VOLATILITY_THRESHOLD', '0.05'))
            low_vol_threshold = float(os.getenv('LOW_VOLATILITY_THRESHOLD', '0.01'))
            high_vol_impact = float(os.getenv('HIGH_VOLATILITY_WIN_RATE_IMPACT', '0.8'))
            low_vol_impact = float(os.getenv('LOW_VOLATILITY_WIN_RATE_IMPACT', '0.9'))
            trend_impact_multiplier = float(os.getenv('TREND_IMPACT_ON_WIN_RATE_MULTIPLIER', '0.5'))
            max_trend_impact = float(os.getenv('MAX_TREND_IMPACT_ON_WIN_RATE', '0.2'))

            volatility = market_data.get('volatility', float(os.getenv('DEFAULT_ASSET_VOLATILITY', '0.02')))
            trend_strength = abs(market_data.get('trend_strength', 0.0))

            # Very high volatility may reduce win rate (configurable impact)
            if volatility > high_vol_threshold:
                base_win_rate *= high_vol_impact
            elif volatility < low_vol_threshold:
                base_win_rate *= low_vol_impact  # Very low volatility might mean fewer opportunities
            else:
                base_win_rate *= (1.0 + min(max_trend_impact, trend_strength * trend_impact_multiplier))

        # Ensure win rate is between configurable bounds (break-even with 1:1 RR and maximum)
        min_win_rate = float(os.getenv('MINIMUM_WIN_RATE_THRESHOLD', '0.4'))
        max_win_rate = float(os.getenv('MAXIMUM_WIN_RATE_THRESHOLD', '0.9'))
        return max(min_win_rate, min(max_win_rate, base_win_rate))

    def _estimate_reward_risk_ratio(self, signal: Signal, market_data: Optional[Dict[str, Any]]) -> float:
        """Estimate the reward:risk ratio of the signal"""
        # Base reward:risk on market conditions and signal type using configurable defaults
        base_rr = float(os.getenv('BASE_REWARD_RISK_RATIO', '1.5'))  # Default ratio from config

        if market_data:
            default_volatility = float(os.getenv('DEFAULT_ASSET_VOLATILITY', '0.02'))
            volatility_max_rr_impact = float(os.getenv('VOLATILITY_MAX_RR_IMPACT', '0.5'))
            volatility_multiplier = float(os.getenv('VOLATILITY_RR_MULTIPLIER', '10.0'))
            trend_max_rr_impact = float(os.getenv('TREND_MAX_RR_IMPACT', '0.3'))
            trend_multiplier = float(os.getenv('TREND_RR_MULTIPLIER', '2.0'))

            volatility = market_data.get('volatility', default_volatility)
            trend_strength = abs(market_data.get('trend_strength', 0.0))

            # In high volatility, might expect higher RR (configurable impact)
            base_rr *= (1.0 + min(volatility_max_rr_impact, volatility * volatility_multiplier))
            # In strong trends, might get better RR (configurable impact)
            base_rr *= (1.0 + min(trend_max_rr_impact, trend_strength * trend_multiplier))

        # Adjust based on signal confidence with configurable parameters
        confidence = float(signal.confidence.value)
        min_confidence_factor = float(os.getenv('MIN_CONFIDENCE_RR_FACTOR', '0.7'))
        confidence_multiplier = float(os.getenv('CONFIDENCE_RR_MULTIPLIER', '0.6'))
        confidence_based_adjustment = min_confidence_factor + (confidence * confidence_multiplier)  # RR between ~min_confidence_factor*base and (min_confidence_factor + confidence_multiplier)*base based on confidence
        base_rr *= confidence_based_adjustment

        # Limit between configurable bounds
        min_rr = float(os.getenv('MIN_REWARD_RISK_RATIO', '0.5'))
        max_rr = float(os.getenv('MAX_REWARD_RISK_RATIO', '5.0'))
        return max(min_rr, min(max_rr, base_rr))

    def _estimate_asset_volatility(self, signal: Signal, market_data: Optional[Dict[str, Any]]) -> float:
        """Estimate the volatility of the asset"""
        # Use configurable default if no data available
        default_vol = float(os.getenv('DEFAULT_ANNUAL_VOLATILITY', '0.20'))

        if market_data and 'volatility' in market_data:
            return market_data['volatility']
        elif market_data and 'atr' in market_data and 'price' in market_data:
            # Convert ATR to volatility proxy
            atr = market_data['atr']
            price = market_data['price']
            if price > 0:
                # Configurable multiplier for ATR to volatility conversion
                atr_to_vol_multiplier = float(os.getenv('ATR_TO_VOLATILITY_MULTIPLIER', '1.0'))
                return (atr / price) * atr_to_vol_multiplier  # Rough approximation with configurable factor

        return default_vol

    def get_position_size_recommendation(self, 
                                       signal: Signal, 
                                       portfolio_value: float, 
                                       market_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get position size recommendation using multiple algorithms"""
        recommendations = {}
        
        # Calculate position size using multiple algorithms
        algorithms = [
            'kelly',
            'fixed_fractional', 
            'atr_based',
            'correlation_adjusted',
            'optimal_f',
            'volatility_targeted'
        ]
        
        for algorithm in algorithms:
            try:
                size = self.calculate_position_size(signal, portfolio_value, algorithm, market_data)
                recommendations[algorithm] = size
            except Exception as e:
                logger.error(f"Error calculating {algorithm} position size: {e}")
                recommendations[algorithm] = 0.0
        
        # Return the most conservative recommendation (minimum of all suggestions)
        final_position_size = min([size for size in recommendations.values() if size > 0], default=portfolio_value * 0.01)
        
        result = {
            'recommendations': recommendations,
            'final_position_size': final_position_size,
            'portfolio_utilization': final_position_size / portfolio_value if portfolio_value > 0 else 0,
            'algorithm_used': 'conservative_min'  # Using minimum of all algorithms
        }
        
        logger.info(f"Position sizing recommendation: ${final_position_size:,.2f} "
                   f"({result['portfolio_utilization']:.2%} of portfolio)")
        return result