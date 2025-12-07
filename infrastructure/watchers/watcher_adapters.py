"""
Infrastructure implementations of market watchers.
"""
from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol, Percentage
from domain.ports.watcher_ports import WatcherPort
from shared.logger import EnhancedLogger, logger
from datetime import datetime
from decimal import Decimal


class BaseWatcherAdapter(WatcherPort):
    """Base class for watcher adapters implementing WatcherPort"""

    def __init__(self, name: str, symbol: Symbol):
        self.name = name
        self.symbol = symbol
        self._is_running = False
        self.last_signal: Optional[Signal] = None
        self.logger = EnhancedLogger(f"{name}_{symbol.value}")

    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market conditions and return a signal"""
        # This should be implemented by subclasses
        raise NotImplementedError

    def start(self):
        """Start the watcher"""
        self._is_running = True
        self.logger.log_watcher_analysis(self.name, self.symbol.value, "Started")

    def stop(self):
        """Stop the watcher"""
        self._is_running = False
        self.logger.log_watcher_analysis(self.name, self.symbol.value, "Stopped")
    
    def update_data(self, data: Dict[str, Any]):
        """Update the watcher with new market data"""
        # Base implementation - can be overridden by specific watchers
        pass
    
    def is_running(self) -> bool:
        """Check if the watcher is currently running"""
        return self._is_running
    
    def should_emit_signal(self, current_signal: Signal) -> bool:
        """Determine if a new signal should be emitted"""
        if not self.last_signal:
            return True

        # Don't emit if the same signal was generated recently with similar confidence
        return (current_signal.signal_type != self.last_signal.signal_type or
                abs(float(current_signal.confidence.value) - float(self.last_signal.confidence.value)) > 0.1)


class MarketPulseWatcherAdapter(BaseWatcherAdapter):
    """Infrastructure implementation of market pulse watcher"""
    
    def __init__(self, symbol: Symbol):
        super().__init__("MarketPulse", symbol)
        self.lookback_period = 10  # periods to look back for momentum
        self.momentum_threshold = 0.02  # 2% threshold for momentum signals
    
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market momentum and generate signals"""
        self.logger.log_watcher_analysis(self.name, symbol.value, "Analyzing market momentum")

        # In a real implementation, this would analyze momentum indicators
        # For demonstration, we'll create a mock signal

        from domain.entities.trading_entities import SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal

        # Mock momentum analysis
        momentum_score = 0.6  # This would come from actual momentum calculation
        confidence = Percentage(Decimal('0.7'))  # 70% confidence

        # Determine signal type based on momentum
        if momentum_score > 0.3:
            signal_type = SignalType.BUY
        elif momentum_score < -0.3:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=momentum_score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="MarketPulse",
            metadata={
                'momentum_score': momentum_score,
                'indicator': 'RSI-based momentum'
            }
        )

        # Only emit if the signal is significant enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            confidence_val = float(signal.confidence.value)
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Generated {signal.signal_type.name} signal", confidence=confidence_val, signal_type=signal.signal_type.name)
            return signal
        else:
            self.logger.log_watcher_analysis(self.name, symbol.value, "Signal filtered due to similarity with previous signal")
            return None
    
    def update_data(self, data: Dict[str, Any]):
        """Update with new market data"""
        # Process market data updates
        pass


class VolatilityWatcherAdapter(BaseWatcherAdapter):
    """Infrastructure implementation of volatility watcher"""
    
    def __init__(self, symbol: Symbol):
        super().__init__("Volatility", symbol)
        self.lookback_period = 20
        self.volatility_threshold_high = 0.03  # High volatility threshold
        self.volatility_threshold_low = 0.01   # Low volatility threshold
    
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market volatility and generate alerts"""
        self.logger.log_watcher_analysis(self.name, symbol.value, "Analyzing market volatility")

        from domain.entities.trading_entities import SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal

        # Mock volatility analysis
        volatility_score = 0.4  # This would come from actual volatility calculation

        # Volatility watchers typically generate alerts about market conditions
        # rather than direct buy/sell signals, but we'll create a signal for consistency
        if volatility_score > 0.6:  # High volatility
            signal_type = SignalType.HOLD  # Suggest caution in high volatility
            confidence = Percentage(Decimal('0.8'))
            score = -0.5  # Negative score indicating caution
        elif volatility_score < 0.3:  # Low volatility
            signal_type = SignalType.NEUTRAL
            confidence = Percentage(Decimal('0.6'))
            score = 0.2   # Slight positive bias in low volatility
        else:  # Normal volatility
            signal_type = SignalType.NEUTRAL
            confidence = Percentage(Decimal('0.5'))
            score = 0.0   # Neutral score

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="Volatility",
            metadata={
                'volatility_score': volatility_score,
                'market_regime': 'high_volatility' if volatility_score > 0.6 else 'normal_volatility' if 0.3 <= volatility_score <= 0.6 else 'low_volatility'
            }
        )

        if self.should_emit_signal(signal):
            self.last_signal = signal
            confidence_val = float(signal.confidence.value)
            regime = 'high_volatility' if volatility_score > 0.6 else 'normal_volatility' if 0.3 <= volatility_score <= 0.6 else 'low_volatility'
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Generated {signal.signal_type.name} signal in {regime} regime", confidence=confidence_val, signal_type=signal.signal_type.name, regime=regime)
            return signal
        else:
            regime = 'high_volatility' if volatility_score > 0.6 else 'normal_volatility' if 0.3 <= volatility_score <= 0.6 else 'low_volatility'
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Volatility analysis completed, no signal generated (regime: {regime})", regime=regime)
            return None
    
    def update_data(self, data: Dict[str, Any]):
        """Update with new market data"""
        # Process volatility-related market data
        pass


class TrendMTFWatcherAdapter(BaseWatcherAdapter):
    """Infrastructure implementation of multi-timeframe trend watcher"""
    
    def __init__(self, symbol: Symbol):
        super().__init__("TrendMTF", symbol)
        self.timeframes = ['5m', '15m', '30m']  # Multiple timeframes optimized for crypto scalping
    
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze trends across multiple timeframes"""
        self.logger.log_watcher_analysis(self.name, symbol.value, f"Analyzing trends across timeframes: {self.timeframes}")

        from domain.entities.trading_entities import SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal

        # Mock multi-timeframe analysis
        # In reality, this would analyze trends on multiple timeframes
        trend_alignment = 0.8  # How aligned are trends across timeframes (0 to 1)

        if trend_alignment > 0.7:
            # Strong trend alignment
            signal_type = SignalType.BUY if trend_alignment > 0.75 else SignalType.SELL
            confidence = Percentage(Decimal(str(min(1.0, trend_alignment * 1.2))))  # Boost confidence with alignment
            score = trend_alignment if trend_alignment > 0.75 else -trend_alignment
        elif trend_alignment < 0.3:
            # Opposing trends
            signal_type = SignalType.HOLD
            confidence = Percentage(Decimal('0.4'))
            score = 0.0
        else:
            # Mixed signals
            signal_type = SignalType.NEUTRAL
            confidence = Percentage(Decimal('0.5'))
            score = 0.1 if trend_alignment > 0.5 else -0.1

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="TrendMTF",
            metadata={
                'trend_alignment': trend_alignment,
                'timeframes_analyzed': self.timeframes,
                'multi_timeframe_score': trend_alignment
            }
        )

        if self.should_emit_signal(signal):
            self.last_signal = signal
            confidence_val = float(signal.confidence.value)
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Generated {signal.signal_type.name} signal with {trend_alignment:.2%} trend alignment across {len(self.timeframes)} timeframes", confidence=confidence_val, signal_type=signal.signal_type.name, trend_alignment=trend_alignment, timeframes=len(self.timeframes))
            return signal
        else:
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Trend analysis completed, no signal generated (alignment: {trend_alignment:.2%})", trend_alignment=trend_alignment)
            return None
    
    def update_data(self, data: Dict[str, Any]):
        """Update with new market data"""
        # Process multi-timeframe market data
        pass


class AnomalyMLWatcherAdapter(BaseWatcherAdapter):
    """Infrastructure implementation of ML-based anomaly watcher"""
    
    def __init__(self, symbol: Symbol):
        super().__init__("AnomalyML", symbol)
        self.model_confidence_threshold = 0.7
        self.anomaly_sensitivity = 0.1  # Lower = more sensitive
    
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market anomalies using ML models"""
        self.logger.log_watcher_analysis(self.name, symbol.value, "Analyzing market anomalies with ML models")

        from domain.entities.trading_entities import SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal

        # Mock ML anomaly detection
        anomaly_score = 0.75  # This would come from an actual ML model
        anomaly_type = 'price_volume_deviation' if anomaly_score > 0.8 else 'normal'

        if anomaly_score > self.model_confidence_threshold:
            # Significant anomaly detected - potential opportunity or risk
            # Anomalies can indicate either reversal or continuation opportunities
            signal_type = SignalType.BUY if anomaly_score > 0.8 else SignalType.SELL
            confidence = Percentage(Decimal(str(anomaly_score)))
            score = anomaly_score if signal_type == SignalType.BUY else -anomaly_score
        else:
            # No significant anomaly
            signal_type = SignalType.NEUTRAL
            confidence = Percentage(Decimal('0.3'))
            score = 0.0

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="AnomalyML",
            metadata={
                'anomaly_score': anomaly_score,
                'ml_model': 'isolation_forest',
                'anomaly_type': anomaly_type
            }
        )

        if self.should_emit_signal(signal):
            self.last_signal = signal
            confidence_val = float(signal.confidence.value)
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Generated {signal.signal_type.name} signal based on {anomaly_type} anomaly (score: {anomaly_score:.2f})", confidence=confidence_val, signal_type=signal.signal_type.name, anomaly_type=anomaly_type, anomaly_score=anomaly_score)
            return signal
        else:
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Anomaly analysis completed, no signal generated (score: {anomaly_score:.2f}, type: {anomaly_type})", anomaly_type=anomaly_type, anomaly_score=anomaly_score)
            return None
    
    def update_data(self, data: Dict[str, Any]):
        """Update with new market data"""
        # Process market data for ML model
        pass


class OrderFlowWatcherAdapter(BaseWatcherAdapter):
    """Infrastructure implementation of order flow watcher"""
    
    def __init__(self, symbol: Symbol):
        super().__init__("OrderFlow", symbol)
        self.volume_threshold = 2.0  # Multiple of average volume
    
    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze order flow patterns"""
        self.logger.log_watcher_analysis(self.name, symbol.value, "Analyzing order flow patterns and liquidity")

        from domain.entities.trading_entities import SignalType
        from domain.value_objects import Percentage
        from decimal import Decimal

        # Mock order flow analysis
        order_flow_imbalance = 0.65  # This would come from actual order flow data
        liquidity_assessment = 'high' if order_flow_imbalance > 0.6 else 'normal'

        if order_flow_imbalance > 0.7:
            # Strong buy pressure
            signal_type = SignalType.BUY
            confidence = Percentage(Decimal('0.85'))
            score = order_flow_imbalance
        elif order_flow_imbalance < 0.3:
            # Strong sell pressure
            signal_type = SignalType.SELL
            confidence = Percentage(Decimal('0.85'))
            score = -order_flow_imbalance
        else:
            # Balanced order flow
            signal_type = SignalType.NEUTRAL
            confidence = Percentage(Decimal('0.4'))
            score = 0.1 if order_flow_imbalance > 0.5 else -0.1

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="OrderFlow",
            metadata={
                'order_flow_imbalance': order_flow_imbalance,
                'volume_spikes_detected': order_flow_imbalance > 0.8,
                'liquidity_assessment': liquidity_assessment
            }
        )

        if self.should_emit_signal(signal):
            self.last_signal = signal
            confidence_val = float(signal.confidence.value)
            volume_spikes = "Yes" if order_flow_imbalance > 0.8 else "No"
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Generated {signal.signal_type.name} signal (imbalance: {order_flow_imbalance:.2f}, liquidity: {liquidity_assessment}, volume_spikes: {volume_spikes})", confidence=confidence_val, signal_type=signal.signal_type.name, imbalance=order_flow_imbalance, liquidity=liquidity_assessment, volume_spikes=volume_spikes)
            return signal
        else:
            volume_spikes = "Yes" if order_flow_imbalance > 0.8 else "No"
            self.logger.log_watcher_analysis(self.name, symbol.value, f"Order flow analysis completed, no signal generated (imbalance: {order_flow_imbalance:.2f}, liquidity: {liquidity_assessment}, volume_spikes: {volume_spikes})", imbalance=order_flow_imbalance, liquidity=liquidity_assessment, volume_spikes=volume_spikes)
            return None
    
    def update_data(self, data: Dict[str, Any]):
        """Update with new market data"""
        # Process order flow data
        pass