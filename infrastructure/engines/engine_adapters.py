"""
Infrastructure implementations of real trading engines for the enterprise hedge fund system.
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import numpy as np

from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol, Percentage, Money
from domain.ports.engine_ports import EnginePort
from shared.logger import logger


class TrendEngineAdapter(EnginePort):
    """Infrastructure implementation of trend engine following hexagonal architecture"""
    
    def __init__(self, lookback: int = 20, trend_threshold: float = 0.01):
        self.name = "TrendEngine"
        self.lookback = lookback
        self.trend_threshold = trend_threshold
        self.price_history: List[float] = []
        self.trend_direction = 0  # -1 for down, 0 for neutral, 1 for up
        self.current_trend_strength = 0.0

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through trend analysis"""
        if len(self.price_history) < 5:
            # Not enough data - return original signal with slightly reduced confidence
            new_confidence_value = signal.confidence.value * Decimal('0.8')
            new_confidence = Percentage(max(Decimal('0.0'), min(Decimal('1.0'), new_confidence_value)))
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.8,
                strategy_name=f"{signal.strategy_name}_trend_filtered",
                timestamp=datetime.now(),
                source_engine=self.name,
                metadata=signal.metadata or {}
            )

        # Check if the incoming signal aligns with the current trend
        signal_aligns_with_trend = (
            (self.trend_direction == 1 and signal.signal_type.name == 'BUY') or
            (self.trend_direction == -1 and signal.signal_type.name == 'SELL')
        )

        if signal_aligns_with_trend:
            # Signal aligns with trend - increase confidence
            new_confidence_value = signal.confidence.value * Decimal('1.2')
            new_confidence = min(Percentage(Decimal('1.0')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = min(1.0, signal.score * 1.2)
        else:
            # Signal goes against trend - decrease confidence
            new_confidence_value = signal.confidence.value * Decimal('0.7')
            new_confidence = max(Percentage(Decimal('0.2')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = max(-1.0, signal.score * 0.7)

        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy_name=f"{signal.strategy_name}_trend_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'trend_aligned': signal_aligns_with_trend,
                'trend_direction': self.trend_direction,
                'trend_strength': self.current_trend_strength
            }
        )

        logger.info(f"TrendEngine processed signal: {signal.signal_type.name} -> {enhanced_signal.signal_type.name}, "
                   f"confidence: {float(signal.confidence):.2%} -> {float(enhanced_signal.confidence):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        # Process all signals in this simple implementation
        return True

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update engine with new market data"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback * 3:
                self.price_history.pop(0)

            # Update trend if we have enough data
            if len(self.price_history) >= self.lookback:
                self._update_trend()

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name

    def _update_trend(self):
        """Update the current trend direction"""
        if len(self.price_history) < 5:
            return

        # Calculate simple trend using linear regression
        prices = np.array(self.price_history[-self.lookback:])
        x = np.arange(len(prices))

        # Calculate slope
        if len(x) > 1:
            slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

            # Calculate average price for normalization
            avg_price = np.mean(prices)

            if avg_price != 0:
                # Normalize slope by average price to get trend strength
                normalized_slope = slope / avg_price
                self.current_trend_strength = normalized_slope

                # Determine trend direction
                if normalized_slope > self.trend_threshold:
                    self.trend_direction = 1
                elif normalized_slope < -self.trend_threshold:
                    self.trend_direction = -1
                else:
                    self.trend_direction = 0


class VolatilityEngineAdapter(EnginePort):
    """Infrastructure implementation of volatility engine following hexagonal architecture"""
    
    def __init__(self, lookback: int = 20, high_vol_threshold: float = 0.02, low_vol_threshold: float = 0.005):
        self.name = "VolatilityEngine"
        self.lookback = lookback
        self.high_vol_threshold = high_vol_threshold  # High volatility threshold (2%)
        self.low_vol_threshold = low_vol_threshold    # Low volatility threshold (0.5%)
        self.price_history: List[float] = []
        self.volatility_history: List[float] = []
        self.current_volatility = 0
        self.avg_volatility = 0

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through volatility analysis"""
        if not self.volatility_history:
            # No volatility data - return original signal with slightly reduced confidence
            new_confidence_value = signal.confidence.value * Decimal('0.9')
            new_confidence = Percentage(max(Decimal('0.0'), min(Decimal('1.0'), new_confidence_value)))
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.9,
                strategy_name=f"{signal.strategy_name}_vol_filtered",
                timestamp=datetime.now(),
                source_engine=self.name,
                metadata=signal.metadata or {}
            )

        # Determine volatility regime
        is_high_vol = self.current_volatility > self.high_vol_threshold
        is_low_vol = self.current_volatility < self.low_vol_threshold
        is_normal_vol = not is_high_vol and not is_low_vol

        # Adjust signal based on volatility regime
        if is_high_vol:
            # High volatility may mean uncertain signals, reduce confidence
            new_confidence_value = signal.confidence.value * Decimal('0.6')
            new_confidence = max(Percentage(Decimal('0.2')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = signal.score * 0.7
        elif is_low_vol:
            # Low volatility may mean signals are more reliable, slightly increase confidence
            new_confidence_value = signal.confidence.value * Decimal('1.1')
            new_confidence = min(Percentage(Decimal('1.0')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = signal.score * 1.1
        else:
            # Normal volatility - keep confidence relatively unchanged
            new_confidence = signal.confidence
            new_score = signal.score

        # For contrarian signals, volatility adjustment might be different
        is_contrarian = (signal.metadata or {}).get('contrarian', False) if signal.metadata else False
        if is_contrarian and is_high_vol:
            # High volatility might validate contrarian signals
            new_confidence_value = new_confidence.value * Decimal('1.2')
            new_confidence = min(Percentage(Decimal('1.0')), Percentage(max(Decimal('0.0'), new_confidence_value)))

        # Generate enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy_name=f"{signal.strategy_name}_vol_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'volatility_regime': 'high' if is_high_vol else 'low' if is_low_vol else 'normal',
                'current_volatility': self.current_volatility,
                'is_contrarian': is_contrarian
            }
        )

        logger.info(f"VolatilityEngine processed signal: {signal.signal_type.name}, "
                   f"volatility regime: {'high' if is_high_vol else 'low' if is_low_vol else 'normal'}, "
                   f"confidence: {float(signal.confidence):.2%} -> {float(enhanced_signal.confidence):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        return True

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback * 3:
                self.price_history.pop(0)

            # Calculate volatility if we have enough data
            if len(self.price_history) >= 2:
                returns = np.diff(self.price_history[-self.lookback-1:]) / np.array(self.price_history[-self.lookback-1:-1])
                if len(returns) > 1:
                    vol = np.std(returns)
                    self.volatility_history.append(vol)
                    if len(self.volatility_history) > self.lookback * 3:
                        self.volatility_history.pop(0)

                    self.current_volatility = vol
                    self.avg_volatility = np.mean(self.volatility_history) if self.volatility_history else 0

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name


class LiquidityEngineAdapter(EnginePort):
    """Infrastructure implementation of liquidity engine following hexagonal architecture"""
    
    def __init__(self, lookback: int = 10, low_liquidity_threshold: float = 0.3, high_liquidity_threshold: float = 0.7):
        self.name = "LiquidityEngine"
        self.lookback = lookback
        self.low_liquidity_threshold = low_liquidity_threshold
        self.high_liquidity_threshold = high_liquidity_threshold
        self.bids: List[tuple] = []  # List of (price, volume) tuples
        self.asks: List[tuple] = []  # List of (price, volume) tuples
        self.liquidity_score_history: List[float] = []
        self.current_liquidity_score = 0.0
        self.avg_liquidity_score = 0.0

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through liquidity analysis"""
        if not self.liquidity_score_history:
            # No liquidity data - return original signal
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                score=signal.score,
                strategy_name=signal.strategy_name,
                timestamp=datetime.now(),
                source_engine=self.name,
                metadata=signal.metadata or {}
            )

        # Get current liquidity regime
        is_low_liquidity = self.current_liquidity_score < self.low_liquidity_threshold
        is_high_liquidity = self.current_liquidity_score > self.high_liquidity_threshold
        is_normal_liquidity = not (is_low_liquidity or is_high_liquidity)

        # Adjust signal based on liquidity regime
        if is_low_liquidity:
            # In low liquidity, reduce position sizes and confidence
            new_confidence_value = signal.confidence.value * Decimal('0.6')
            new_confidence = max(Percentage(Decimal('0.2')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = signal.score * 0.7
        elif is_high_liquidity:
            # In high liquidity, confidence can be increased slightly
            new_confidence_value = signal.confidence.value * Decimal('1.1')
            new_confidence = min(Percentage(Decimal('1.0')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = signal.score * 1.05
        else:
            # Normal liquidity - pass through with minor adjustments
            new_confidence = signal.confidence
            new_score = signal.score

        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy_name=f"{signal.strategy_name}_liquid_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'liquidity_regime': 'low' if is_low_liquidity else 'high' if is_high_liquidity else 'normal',
                'liquidity_score': self.current_liquidity_score
            }
        )

        logger.info(f"LiquidityEngine processed signal: {signal.signal_type.name}, "
                   f"liquidity regime: {'low' if is_low_liquidity else 'high' if is_high_liquidity else 'normal'}, "
                   f"confidence: {float(signal.confidence):.2%} -> {float(enhanced_signal.confidence):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        return True

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data (order book)"""
        if 'bids' in data and 'asks' in data:
            # Update order book
            self.bids = [(float(price), float(vol)) for price, vol in data['bids']]
            self.asks = [(float(price), float(vol)) for price, vol in data['asks']]

            # Calculate liquidity metrics
            liquidity_score = self._calculate_liquidity_score()
            self.liquidity_score_history.append(liquidity_score)
            if len(self.liquidity_score_history) > self.lookback * 3:
                self.liquidity_score_history.pop(0)

            self.current_liquidity_score = liquidity_score
            self.avg_liquidity_score = np.mean(self.liquidity_score_history) if self.liquidity_score_history else 0.5

    def _calculate_liquidity_score(self) -> float:
        """Calculate a liquidity score from 0 to 1"""
        if not self.bids or not self.asks:
            return 0.0

        # Calculate total volume in the top levels
        top_bid_vol = sum(vol for _, vol in self.bids[:5])  # Top 5 bid levels
        top_ask_vol = sum(vol for _, vol in self.asks[:5])  # Top 5 ask levels

        # Calculate spread
        best_bid = self.bids[0][0] if self.bids else 1
        best_ask = self.asks[0][0] if self.asks else 1
        spread = (best_ask - best_bid) / best_bid if best_bid != 0 else 0

        # Calculate depth score (how much volume is available at good prices)
        total_top_volume = top_bid_vol + top_ask_vol
        avg_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 1
        dollar_depth = total_top_volume * avg_price

        # Combine spread and depth to create liquidity score
        # Lower spread and higher depth = higher liquidity
        spread_factor = max(0, 1 - spread * 100)  # Convert spread to factor (0-1), assuming 1% max spread
        depth_factor = min(1, np.log1p(dollar_depth / 10000) / 5)  # Logarithmic scaling for depth

        # Weighted combination (can be adjusted)
        liquidity_score = (spread_factor * 0.4) + (depth_factor * 0.6)

        return max(0.0, min(1.0, liquidity_score))  # Clamp between 0 and 1

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name


class OrderFlowEngineAdapter(EnginePort):
    """Infrastructure implementation of order flow engine following hexagonal architecture"""
    
    def __init__(self, lookback: int = 20):
        self.name = "OrderFlowEngine"
        self.lookback = lookback

        # Order book data
        self.bids: List[tuple] = []  # (price, volume)
        self.asks: List[tuple] = []  # (price, volume)

        # Order flow metrics
        self.bid_volume_history: List[float] = []
        self.ask_volume_history: List[float] = []
        self.order_flow_imbalance_history: List[float] = []
        self.aggressive_buy_volume = 0
        self.aggressive_sell_volume = 0

        # Calculated metrics
        self.current_imbalance = 0
        self.avg_imbalance = 0
        self.imbalance_trend = 0

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through order flow analysis"""
        if len(self.order_flow_imbalance_history) < 3:
            # Not enough order flow data - return original signal with slightly reduced confidence
            new_confidence_value = signal.confidence.value * Decimal('0.85')
            new_confidence = Percentage(max(Decimal('0.0'), min(Decimal('1.0'), new_confidence_value)))
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=new_confidence,
                score=signal.score * 0.85,
                strategy_name=f"{signal.strategy_name}_of_filtered",
                timestamp=datetime.now(),
                source_engine=self.name,
                metadata=signal.metadata or {}
            )

        # Determine order flow regime
        is_buy_pressure = self.current_imbalance > 0.3
        is_sell_pressure = self.current_imbalance < -0.3
        is_neutral_pressure = not (is_buy_pressure or is_sell_pressure)

        # Adjust signal based on order flow
        if is_buy_pressure and signal.signal_type.name == 'BUY':
            # Buy signal aligns with buy pressure - boost confidence
            new_confidence_value = signal.confidence.value * Decimal('1.25')
            new_confidence = min(Percentage(Decimal('1.0')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = min(1.0, signal.score * 1.25)
        elif is_sell_pressure and signal.signal_type.name == 'SELL':
            # Sell signal aligns with sell pressure - boost confidence
            new_confidence_value = signal.confidence.value * Decimal('1.25')
            new_confidence = min(Percentage(Decimal('1.0')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = max(-1.0, signal.score * 1.25)
        elif is_buy_pressure and signal.signal_type.name == 'SELL':
            # Sell signal against buy pressure - reduce confidence significantly
            new_confidence_value = signal.confidence.value * Decimal('0.6')
            new_confidence = max(Percentage(Decimal('0.2')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = max(-1.0, signal.score * 0.6)
        elif is_sell_pressure and signal.signal_type.name == 'BUY':
            # Buy signal against sell pressure - reduce confidence significantly
            new_confidence_value = signal.confidence.value * Decimal('0.6')
            new_confidence = max(Percentage(Decimal('0.2')), Percentage(max(Decimal('0.0'), new_confidence_value)))
            new_score = min(1.0, signal.score * 0.6)
        else:
            # Neutral pressure or unclear alignment - slight adjustment
            new_confidence = signal.confidence
            new_score = signal.score

        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy_name=f"{signal.strategy_name}_of_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'order_flow_regime': 'buy_pressure' if is_buy_pressure else 'sell_pressure' if is_sell_pressure else 'neutral',
                'order_flow_imbalance': self.current_imbalance,
                'pressure_trend': self.imbalance_trend
            }
        )

        logger.info(f"OrderFlowEngine processed signal: {signal.signal_type.name}, "
                   f"flow regime: {'buy' if is_buy_pressure else 'sell' if is_sell_pressure else 'neutral'}, "
                   f"confidence: {float(signal.confidence):.2%} -> {float(enhanced_signal.confidence):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        return True

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data (order book and trades)"""
        if 'bids' in data and 'asks' in data:
            self.bids = [(float(price), float(vol)) for price, vol in data['bids']]
            self.asks = [(float(price), float(vol)) for price, vol in data['asks']]

            # Calculate total volumes
            bid_vol = sum(vol for _, vol in self.bids)
            ask_vol = sum(vol for _, vol in self.asks)

            self.bid_volume_history.append(bid_vol)
            self.ask_volume_history.append(ask_vol)

            if len(self.bid_volume_history) > self.lookback * 3:
                self.bid_volume_history.pop(0)
                self.ask_volume_history.pop(0)

            # Calculate order flow imbalance
            total_vol = bid_vol + ask_vol
            if total_vol > 0:
                imbalance = (bid_vol - ask_vol) / total_vol
            else:
                imbalance = 0

            self.order_flow_imbalance_history.append(imbalance)

            if len(self.order_flow_imbalance_history) > self.lookback * 3:
                self.order_flow_imbalance_history.pop(0)

            # Update calculated metrics
            self.current_imbalance = imbalance
            self.avg_imbalance = np.mean(self.order_flow_imbalance_history) if self.order_flow_imbalance_history else 0

            # Calculate imbalance trend
            if len(self.order_flow_imbalance_history) >= 2:
                recent_imbalances = self.order_flow_imbalance_history[-5:] if len(self.order_flow_imbalance_history) >= 5 else self.order_flow_imbalance_history
                x = np.arange(len(recent_imbalances))
                if len(x) > 1:
                    denominator = len(x) * np.sum(x * x) - (np.sum(x)) ** 2
                    if denominator != 0:
                        self.imbalance_trend = (len(x) * np.sum(x * recent_imbalances) - np.sum(x) * np.sum(recent_imbalances)) / denominator
                    else:
                        self.imbalance_trend = 0
                else:
                    self.imbalance_trend = 0
            else:
                self.imbalance_trend = 0

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name


class RegimeEngineAdapter(EnginePort):
    """Infrastructure implementation of regime detection engine following hexagonal architecture"""
    
    def __init__(self, lookback: int = 30):
        self.name = "RegimeEngine"
        self.lookback = lookback

        # Market data history
        self.price_history: List[float] = []
        self.volume_history: List[float] = []

        # Regime detection metrics
        self.volatility_regime = "normal"
        self.trend_regime = "sideways"
        self.liquidity_regime = "normal"
        self.momentum_regime = "neutral"

        # Volatility measures
        self.current_volatility = 0
        self.avg_volatility = 0
        self.volatility_regimes = []

        # Trend measures
        self.current_trend_strength = 0
        self.trend_regimes = []

        # Thresholds
        self.high_vol_threshold = 0.025  # High volatility (>2.5% daily)
        self.low_vol_threshold = 0.008   # Low volatility (<0.8% daily)
        self.trend_strength_threshold = 0.003  # Trend strength threshold

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through regime analysis"""
        # Adjust signal based on detected regime
        regime_multipliers = {
            ('trending', 'high'): 1.15,  # Trending markets with high volatility - boost trend-following signals
            ('trending', 'low'): 1.2,    # Trending with low volatility - even better for trends
            ('reverting', 'high'): 1.2,  # Mean-reverting with high volatility - boost counter-trend signals
            ('reverting', 'low'): 1.1,   # Mean-reverting with low volatility - boost but less than high vol
            ('neutral', 'normal'): 1.0,  # Neutral regime - no adjustment
        }

        # Determine regime category based on metrics
        trend_regime_cat = "trending" if abs(self.current_trend_strength) > self.trend_strength_threshold else \
                          ("reverting" if self.current_trend_strength < -self.trend_strength_threshold else "neutral")
        
        vol_regime_cat = "high" if self.current_volatility > self.high_vol_threshold else \
                        ("low" if self.current_volatility < self.low_vol_threshold else "normal")

        regime_key = (trend_regime_cat, vol_regime_cat)
        multiplier = regime_multipliers.get(regime_key, 1.0)

        # Adjust confidence based on regime appropriateness
        is_trend_following = 'trend' in signal.strategy_name.lower()
        is_mean_reverting = 'revert' in signal.strategy_name.lower() or 'mean' in signal.strategy_name.lower()

        effective_multiplier = multiplier
        if is_trend_following and trend_regime_cat == "trending":
            # Extra boost for trend-following in trending regime
            effective_multiplier *= 1.1
        elif is_mean_reverting and trend_regime_cat == "reverting":
            # Extra boost for mean-reversion in reverting regime
            effective_multiplier *= 1.1
        elif is_trend_following and trend_regime_cat == "reverting":
            # Penalty for trend-following in reverting regime
            effective_multiplier *= 0.8
        elif is_mean_reverting and trend_regime_cat == "trending":
            # Penalty for mean-reversion in trending regime
            effective_multiplier *= 0.8

        # Apply regime adjustment
        new_confidence_value = signal.confidence.value * Decimal(str(min(effective_multiplier, 2.0)))
        new_confidence = min(Percentage(Decimal('1.0')),
                           Percentage(max(Decimal('0.0'), new_confidence_value)))
        new_score = max(-1.0, min(1.0, signal.score * effective_multiplier))

        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy_name=f"{signal.strategy_name}_regime_adjusted",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'regime': {
                    'trend_regime': trend_regime_cat,
                    'volatility_regime': vol_regime_cat,
                    'trend_strength': self.current_trend_strength,
                    'volatility': self.current_volatility,
                    'regime_multiplier': effective_multiplier
                }
            }
        )

        logger.info(f"RegimeEngine processed signal: {signal.signal_type.name}, "
                   f"regime: {trend_regime_cat}-{vol_regime_cat}, "
                   f"multiplier: {effective_multiplier:.2f}, "
                   f"confidence: {float(signal.confidence):.2%} -> {float(enhanced_signal.confidence):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        return True

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback * 4:
                self.price_history.pop(0)

        if 'volume' in data:
            self.volume_history.append(float(data['volume']))
            if len(self.volume_history) > self.lookback * 4:
                self.volume_history.pop(0)

        # Update regime metrics if we have enough data
        if len(self.price_history) >= 10:
            self._update_regime_metrics()

    def _update_regime_metrics(self):
        """Update all regime metrics"""
        # Update volatility regime
        if len(self.price_history) >= 10:
            returns = np.diff(self.price_history[-self.lookback-1:]) / np.array(self.price_history[-self.lookback:-1])
            if len(returns) > 1:
                self.current_volatility = float(np.std(returns))

                if self.current_volatility > self.high_vol_threshold:
                    self.volatility_regime = "high"
                elif self.current_volatility < self.low_vol_threshold:
                    self.volatility_regime = "low"
                else:
                    self.volatility_regime = "normal"

                # Calculate average volatility over recent periods
                volatilities = []
                for i in range(max(10, len(self.price_history)-5), len(self.price_history)):
                    if i > 1:
                        subset_returns = np.diff(self.price_history[i-self.lookback:i+1]) / np.array(self.price_history[i-self.lookback:i])
                        if len(subset_returns) > 1:
                            volatilities.append(np.std(subset_returns))
                
                self.avg_volatility = float(np.mean(volatilities)) if volatilities else self.current_volatility

        # Update trend regime
        if len(self.price_history) >= 5:
            prices = np.array(self.price_history[-self.lookback:])
            x = np.arange(len(prices))

            if len(x) > 1:
                slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                        (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

                # Calculate average price for normalization
                avg_price = np.mean(prices) if len(prices) > 0 else 1

                if avg_price != 0:
                    # Normalize slope by average price to get trend strength
                    self.current_trend_strength = slope / avg_price

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name