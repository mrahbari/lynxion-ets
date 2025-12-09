"""
Enhanced engine adapters incorporating additional algorithms from the archive.

This file adds valuable engine implementations from the archive that enhance
the functionality of our hexagonal architecture system.
"""
from domain.ports.engine_ports import EnginePort
from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol, Percentage
from domain.entities.trading_entities import SignalType  # Added this import
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import numpy as np


class BaseEnhancedEngineAdapter(EnginePort):
    """Base class for enhanced engine adapters implementing EnginePort interface"""
    
    def __init__(self, name: str):
        self.name = name
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal and return enhanced signal"""
        raise NotImplementedError
    
    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        return True
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update the engine with new market data"""
        pass
    
    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name


class ATREngineAdapter(BaseEnhancedEngineAdapter):
    """
    Infrastructure adapter for Average True Range (ATR) engine following hexagonal architecture.
    Based on implementation from archive2/engines/atr_engine.py
    """
    
    def __init__(self, atr_period: int = 14):
        super().__init__("ATREngine")
        self.atr_period = atr_period
        self.price_history: List[Dict[str, float]] = []
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through ATR analysis"""
        logger.info(f"ATREngine processing signal for {signal.symbol.value}")
        
        if len(self.price_history) < self.atr_period or len(self.price_history) < 2:
            # Not enough data for ATR calculation - return original signal
            return signal
        
        # Calculate True Range values and ATR
        tr_values = []
        for i in range(1, len(self.price_history)):
            high = self.price_history[i].get('high', self.price_history[i]['close'])
            low = self.price_history[i].get('low', self.price_history[i]['close'])
            prev_close = self.price_history[i-1]['close']
            
            high_low = high - low
            high_close = abs(high - prev_close)
            low_close = abs(low - prev_close)
            
            tr = max(high_low, high_close, low_close)
            tr_values.append(tr)
        
        if not tr_values:
            return signal
            
        # Calculate ATR (Average True Range)
        atr_period_to_calc = min(self.atr_period, len(tr_values)) 
        atr = float(np.mean(tr_values[-atr_period_to_calc:]))
        
        # Calculate volatility based on ATR (relative to price)
        recent_closes = [p['close'] for p in self.price_history[-self.atr_period:]]
        if recent_closes:
            avg_price = float(np.mean(recent_closes))
            volatility = atr / avg_price if avg_price != 0 else 0
        else:
            avg_price = self.price_history[-1]['close']
            volatility = atr / avg_price if avg_price != 0 else 0
        
        # Adjust signal based on volatility level
        if volatility > 0.015:  # High volatility
            # Reduce confidence for high volatility
            new_confidence_val = max(Decimal('0.15'), signal.confidence.value * Decimal('0.75'))
            new_score = max(-1.0, signal.score * 0.8)
        elif volatility < 0.005:  # Low volatility  
            # Increase confidence for low volatility
            new_confidence_val = min(Decimal('1.0'), signal.confidence.value * Decimal('1.15'))
            new_score = min(1.0, signal.score * 1.15)
        else:  # Normal volatility
            # Keep signal mostly unchanged
            new_confidence_val = signal.confidence.value
            new_score = signal.score
        
        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=Percentage(new_confidence_val),
            score=new_score,
            strategy_name=f"{signal.strategy_name}_atr_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'atr_value': atr,
                'volatility_based_on_atr': volatility,
                'atr_period': self.atr_period,
                'atr_analysis_performed': True
            }
        )
        
        logger.info(f"ATREngine enhanced signal: {signal.signal_type.name}, "
                   f"ATR: {atr:.4f}, Volatility: {volatility:.2%}, "
                   f"confidence: {float(signal.confidence.value):.2%} -> {float(enhanced_signal.confidence.value):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process this signal"""
        return len(self.price_history) >= self.atr_period

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data for ATR calculation"""
        if 'close' in data:
            # Create price data object with required fields
            price_point = {
                'high': data.get('high', data['close']),
                'low': data.get('low', data['close']),
                'close': float(data['close']),
                'timestamp': data.get('timestamp', datetime.now().timestamp())
            }
            self.price_history.append(price_point)
            if len(self.price_history) > self.atr_period * 4:
                self.price_history.pop(0)


class EMABreakoutEngineAdapter(BaseEnhancedEngineAdapter):
    """
    Infrastructure adapter for EMA Breakout engine following hexagonal architecture.
    Based on implementation from archive2/engines/ema_engine.py and breakout_engine.py
    """
    
    def __init__(self, short_period: int = 10, long_period: int = 21):
        super().__init__("EMABreakoutEngine")
        self.short_period = short_period
        self.long_period = long_period
        self.price_history: List[float] = []
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through EMA analysis"""
        logger.info(f"EMABreakoutEngine processing signal for {signal.symbol.value}")
        
        if len(self.price_history) < self.long_period:
            # Not enough data for EMA calculation - return original signal
            return signal
        
        # Calculate EMAs
        recent_prices = np.array(self.price_history[-self.long_period:])
        
        # Simple EMA calculation
        def calculate_ema(prices, period):
            if len(prices) < period:
                return np.mean(prices)
            
            ema = np.mean(prices[:period])  # Start with SMA
            multiplier = 2 / (period + 1)
            
            for price in prices[period:]:
                ema = (price - ema) * multiplier + ema
            
            return ema
        
        ema_short = calculate_ema(recent_prices, self.short_period)
        ema_long = calculate_ema(recent_prices, self.long_period)
        
        # Check for EMA crossover
        is_bullish_crossover = ema_short > ema_long
        is_bearish_crossover = ema_short < ema_long
        
        # Check if signal aligns with EMA direction
        signal_is_buy = signal.signal_type.name == 'BUY'
        signal_is_sell = signal.signal_type.name == 'SELL'
        
        ema_aligned = (
            (is_bullish_crossover and signal_is_buy) or
            (is_bearish_crossover and signal_is_sell)
        )
        
        # Adjust signal based on EMA alignment
        if ema_aligned:
            # Boost signals that align with EMA direction
            new_confidence_val = min(Decimal('1.0'), signal.confidence.value * Decimal('1.15'))
            new_score = min(1.0, signal.score * 1.15) if signal_is_buy else max(-1.0, signal.score * 1.15)
        else:
            # Reduce confidence for counter-EMA signals
            new_confidence_val = max(Decimal('0.1'), signal.confidence.value * Decimal('0.85'))
            new_score = max(-1.0, signal.score * 0.85) if signal_is_buy else min(1.0, signal.score * 0.85)
        
        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=Percentage(new_confidence_val),
            score=new_score,
            strategy_name=f"{signal.strategy_name}_ema_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'ema_short': ema_short,
                'ema_long': ema_long,
                'ema_crossover_type': 'bullish' if is_bullish_crossover else 'bearish',
                'ema_aligned': ema_aligned,
                'short_period': self.short_period,
                'long_period': self.long_period
            }
        )
        
        logger.info(f"EMABreakoutEngine enhanced signal: {signal.signal_type.name}, "
                   f"EMA crossover: {'bullish' if is_bullish_crossover else 'bearish'}, "
                   f"EMA aligned: {ema_aligned}, "
                   f"confidence: {float(signal.confidence.value):.2%} -> {float(enhanced_signal.confidence.value):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process this signal"""
        return len(self.price_history) >= self.long_period
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data for EMA calculation"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.long_period * 4:
                self.price_history.pop(0)


class MomentumEngineAdapter(BaseEnhancedEngineAdapter):
    """
    Infrastructure adapter for momentum analysis engine following hexagonal architecture.
    Based on implementation from archive2/engines/momentum_engine.py
    """
    
    def __init__(self, momentum_period: int = 10):
        super().__init__("MomentumEngine")
        self.momentum_period = momentum_period
        self.price_history: List[float] = []
        self.momentum_threshold = 0.02  # 2% momentum threshold
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through momentum analysis"""
        logger.info(f"MomentumEngine processing signal for {signal.symbol.value}")
        
        if len(self.price_history) < self.momentum_period + 1:
            return signal
        
        # Calculate momentum (change over period)
        recent_prices = self.price_history[-(self.momentum_period + 1):]
        momentum_value = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
        
        # Determine momentum regime
        is_high_momentum = abs(momentum_value) > self.momentum_threshold
        is_positive_momentum = momentum_value > 0
        is_negative_momentum = momentum_value < 0
        
        # Check if signal aligns with momentum
        signal_is_buy = signal.signal_type.name == 'BUY'
        signal_is_sell = signal.signal_type.name == 'SELL'
        
        momentum_aligned = (
            (is_positive_momentum and signal_is_buy) or
            (is_negative_momentum and signal_is_sell)
        )
        
        # Adjust signal based on momentum alignment and strength
        if is_high_momentum:
            if momentum_aligned:
                # High momentum in signal direction - increase confidence
                new_confidence_val = min(Decimal('1.0'), signal.confidence.value * Decimal('1.2'))
                new_score = min(1.0, signal.score * 1.2) if signal_is_buy else max(-1.0, signal.score * 1.2)
            else:
                # High momentum against signal - reduce confidence
                new_confidence_val = max(Decimal('0.1'), signal.confidence.value * Decimal('0.6'))
                new_score = signal.score * 0.6
        else:
            # Normal momentum - keep signal mostly unchanged
            new_confidence_val = signal.confidence.value
            new_score = signal.score
        
        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=Percentage(new_confidence_val),
            score=new_score,
            strategy_name=f"{signal.strategy_name}_momentum_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'momentum_value': momentum_value,
                'momentum_strength': abs(momentum_value),
                'momentum_direction': 'positive' if is_positive_momentum else 'negative',
                'is_high_momentum': is_high_momentum,
                'momentum_aligned': momentum_aligned,
                'momentum_period': self.momentum_period
            }
        )
        
        logger.info(f"MomentumEngine enhanced signal: {signal.signal_type.name}, "
                   f"Momentum: {momentum_value:.2%}, "
                   f"Momentum aligned: {momentum_aligned}, "
                   f"confidence: {float(signal.confidence.value):.2%} -> {float(enhanced_signal.confidence.value):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process this signal"""
        return len(self.price_history) >= self.momentum_period + 1
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data for momentum calculation"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.momentum_period * 5:
                self.price_history.pop(0)


class PatternRecognitionEngineAdapter(BaseEnhancedEngineAdapter):
    """
    Infrastructure adapter for pattern recognition engine following hexagonal architecture.
    Based on implementation from archive2/engines/pattern_engine.py
    """
    
    def __init__(self):
        super().__init__("PatternRecognitionEngine")
        self.lookback_period = 20
        self.price_history: List[float] = []
        self.pattern_confidence_threshold = 0.7
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through pattern recognition analysis"""
        logger.info(f"PatternRecognitionEngine processing signal for {signal.symbol.value}")
        
        if len(self.price_history) < 5:
            return signal
        
        # Look for basic patterns in recent price data
        recent_prices = self.price_history[-self.lookback_period:]
        pattern_identified, pattern_confidence = self._identify_pattern(recent_prices)
        
        # If a bullish pattern is identified and we have a buy signal, or
        # if a bearish pattern is identified and we have a sell signal, 
        # increase confidence; otherwise decrease it
        signal_is_buy = signal.signal_type.name == 'BUY'
        signal_is_sell = signal.signal_type.name == 'SELL'
        
        pattern_aligned = False
        if pattern_identified == 'bullish' and signal_is_buy:
            pattern_aligned = True
        elif pattern_identified == 'bearish' and signal_is_sell:
            pattern_aligned = True
        
        # Adjust signal based on pattern alignment
        if pattern_aligned and pattern_confidence > self.pattern_confidence_threshold:
            # Boost signal if pattern strongly supports it
            confidence_boost = min(Decimal('0.2'), Decimal(str(pattern_confidence * 0.2)))
            new_confidence_val = min(Decimal('1.0'), signal.confidence.value + confidence_boost)
            new_score = min(1.0, signal.score * (1 + pattern_confidence * 0.3)) if signal_is_buy else max(-1.0, signal.score * (1 + pattern_confidence * 0.3))
        elif not pattern_aligned and pattern_confidence > self.pattern_confidence_threshold:
            # Reduce confidence if pattern contradicts signal
            confidence_reduction = min(Decimal('0.3'), Decimal(str(pattern_confidence * 0.3)))
            new_confidence_val = max(Decimal('0.1'), signal.confidence.value - confidence_reduction)
            new_score = max(-1.0, signal.score * (1 - pattern_confidence * 0.2)) if signal_is_buy else min(1.0, signal.score * (1 - pattern_confidence * 0.2))
        else:
            # No pattern or low confidence - keep signal unchanged
            new_confidence_val = signal.confidence.value
            new_score = signal.score
        
        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=Percentage(new_confidence_val),
            score=new_score,
            strategy_name=f"{signal.strategy_name}_pattern_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'identified_pattern': pattern_identified,
                'pattern_confidence': pattern_confidence,
                'pattern_aligned': pattern_aligned,
                'pattern_lookback': self.lookback_period
            }
        )
        
        logger.info(f"PatternRecognitionEngine processed signal: {signal.signal_type.name}, "
                   f"identified pattern: {pattern_identified}, "
                   f"pattern aligned: {pattern_aligned}, "
                   f"confidence: {float(signal.confidence.value):.2%} -> {float(enhanced_signal.confidence.value):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process this signal"""
        return len(self.price_history) >= 5
    
    def _identify_pattern(self, prices: List[float]) -> tuple[str, float]:
        """Identify basic patterns in price data"""
        if len(prices) < 3:
            return 'none', 0.0
        
        # Simple pattern detection based on price movement
        changes = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
        
        # Check for consecutive up/down movements
        recent_changes = changes[-5:] if len(changes) >= 5 else changes
        
        # Check for bullish/bearish patterns in the recent changes
        up_count = sum(1 for c in recent_changes if c > 0.001)  # Small threshold for "up" movement
        down_count = sum(1 for c in recent_changes if c < -0.001)  # Small threshold for "down" movement
        
        if up_count >= 3:
            return 'bullish', min(1.0, 0.5 + (up_count * 0.1))
        elif down_count >= 3:
            return 'bearish', min(1.0, 0.5 + (down_count * 0.1))
        else:
            return 'none', 0.0

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data for pattern recognition"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback_period * 3:
                self.price_history.pop(0)


class MicrostructureEngineAdapter(BaseEnhancedEngineAdapter):
    """
    Infrastructure adapter for microstructure analysis engine following hexagonal architecture.
    Based on implementation from archive2/engines/microstructure_engine.py
    """
    
    def __init__(self):
        super().__init__("MicrostructureEngine")
        self.lookback_period = 100
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.order_flow_imbalance_history: List[float] = []
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through microstructure analysis"""
        logger.info(f"MicrostructureEngine processing signal for {signal.symbol.value}")
        
        if len(self.price_history) < 10 or len(self.volume_history) < 10:
            return signal
        
        # Analyze microstructure patterns
        recent_prices = self.price_history[-self.lookback_period:]
        recent_volumes = self.volume_history[-self.lookback_period:]
        
        if not recent_prices or not recent_volumes:
            return signal
        
        # Calculate statistical properties of microstructure
        avg_price = np.mean(recent_prices)
        avg_volume = np.mean(recent_volumes) if recent_volumes else 1.0
        
        # Calculate price clustering (are prices rounding to common levels?)
        rounded_distances = [abs(price - round(price, -int(np.log10(avg_price)) + 2)) for price in recent_prices[-10:]]  # Last 10 for efficiency
        avg_distance_from_round = np.mean(rounded_distances) if rounded_distances else 0.5
        
        # Calculate volume clustering (large trades vs small trades)
        large_trade_threshold = avg_volume * 2.0  # Large trades are 2x average volume
        recent_vols = recent_volumes[-10:] if len(recent_volumes) >= 10 else recent_volumes
        large_trades = [vol for vol in recent_vols if vol > large_trade_threshold]
        large_trade_frequency = len(large_trades) / len(recent_vols) if recent_vols else 0
        
        # Calculate order flow imbalance if available
        ofi_average = np.mean(self.order_flow_imbalance_history[-10:]) if self.order_flow_imbalance_history[-10:] else 0.0
        
        # Adjust signal based on microstructure indicators
        signal_is_buy = signal.signal_type.name == 'BUY'
        signal_is_sell = signal.signal_type.name == 'SELL'

        # Microstructure-based adjustments
        confidence_adjustment = Decimal('0.0')

        # Adjust for price clustering effects (near round numbers might indicate stop-loss hunting)
        if avg_distance_from_round < 0.05:  # Near round numbers
            # Reduce confidence near round numbers (potential manipulation area)
            confidence_adjustment -= Decimal('0.15')

        # Adjust for large trade presence
        if large_trade_frequency > 0.2:  # More than 20% of recent trades are large
            if (ofi_average > 0.1 and signal_is_buy) or (ofi_average < -0.1 and signal_is_sell):
                # Large trades aligned with signal direction - increase confidence
                confidence_adjustment += Decimal('0.15')
            else:
                # Large trades against signal direction - reduce confidence
                confidence_adjustment -= Decimal('0.2')

        # Apply adjustments
        new_confidence_val = max(Decimal('0.1'),
                               min(Decimal('1.0'),
                                   signal.confidence.value + confidence_adjustment))
        new_score = max(-1.0, min(1.0, signal.score))
        
        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=Percentage(new_confidence_val),
            score=new_score,
            strategy_name=f"{signal.strategy_name}_microstructure_enhanced",
            timestamp=datetime.now(),
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'price_clustering_effect': avg_distance_from_round,
                'large_trade_frequency': large_trade_frequency,
                'order_flow_imbalance_avg': ofi_average,
                'microstructure_adjustment': float(adjustment_factor),
                'confidence_adjustment': float(confidence_adjustment)
            }
        )
        
        logger.info(f"MicrostructureEngine processed signal: {signal.signal_type.name}, "
                   f"price clustering: {avg_distance_from_round:.3f}, "
                   f"large trade freq: {large_trade_frequency:.2%}, "
                   f"OFI avg: {ofi_average:.3f}, "
                   f"confidence: {float(signal.confidence.value):.2%} -> {float(enhanced_signal.confidence.value):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process this signal"""
        return len(self.price_history) >= 10 and len(self.volume_history) >= 10
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data for microstructure analysis"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback_period * 3:
                self.price_history.pop(0)
        
        if 'volume' in data:
            self.volume_history.append(float(data['volume']))
            if len(self.volume_history) > self.lookback_period * 3:
                self.volume_history.pop(0)
        
        if 'order_flow_imbalance' in data:
            self.order_flow_imbalance_history.append(float(data['order_flow_imbalance']))
            if len(self.order_flow_imbalance_history) > self.lookback_period * 3:
                self.order_flow_imbalance_history.pop(0)


# Export all enhanced engine adapters
__all__ = [
    'ATREngineAdapter',
    'EMABreakoutEngineAdapter', 
    'MomentumEngineAdapter',
    'PatternRecognitionEngineAdapter',
    'MicrostructureEngineAdapter'
]