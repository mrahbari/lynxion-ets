"""
Infrastructure implementations of engine adapters following hexagonal architecture.
"""
from domain.ports.engine_ports import EnginePort
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import numpy as np
import time
import threading


class EnginePerformanceTracker:
    """Tracks performance metrics for engines."""

    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self.processed_signals = 0
        self.processing_errors = 0
        self.total_processing_time = 0.0
        self.avg_processing_time = 0.0
        self.last_processing_time = 0.0
        self.start_time = time.time()
        self.health_status = "HEALTHY"
        self.lock = threading.Lock()

    def record_processing(self, processing_time: float):
        """Record a successful signal processing."""
        with self.lock:
            self.processed_signals += 1
            self.total_processing_time += processing_time
            self.last_processing_time = processing_time
            self.avg_processing_time = self.total_processing_time / self.processed_signals
            if self.health_status != "ERROR":
                self.health_status = "HEALTHY"

    def record_error(self):
        """Record a processing error."""
        with self.lock:
            self.processing_errors += 1
            self.health_status = "WARNING"  # Could escalate to ERROR based on frequency

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                'engine_name': self.engine_name,
                'processed_signals': self.processed_signals,
                'processing_errors': self.processing_errors,
                'total_processing_time': self.total_processing_time,
                'avg_processing_time': self.avg_processing_time,
                'last_processing_time': self.last_processing_time,
                'uptime_seconds': uptime,
                'health_status': self.health_status,
                'error_rate': self.processing_errors / max(1, self.processed_signals)
            }


class BaseEngineAdapter(EnginePort):
    """Base class for engine adapters implementing the EnginePort interface"""

    def __init__(self, name: str):
        self.name = name
        self.performance_tracker = EnginePerformanceTracker(name)
        self.processing_times = []  # Keep track of recent processing times for optimization

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal and return enhanced signal"""
        start_time = time.time()
        try:
            result = self._process_signal_impl(signal)
            processing_time = time.time() - start_time
            self.performance_tracker.record_processing(processing_time)
            self.processing_times.append(processing_time)

            # Keep only last 100 processing times for optimization
            if len(self.processing_times) > 100:
                self.processing_times = self.processing_times[-100:]

            return result
        except Exception as e:
            processing_time = time.time() - start_time
            self.performance_tracker.record_error()
            logger.error(f"Error processing signal in engine {self.name}: {e}")
            raise

    def _process_signal_impl(self, signal: Signal) -> Signal:
        """Internal method for processing signals - to be overridden by specific engines"""
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

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this engine"""
        return self.performance_tracker.get_performance_metrics()

    def optimize_processing(self):
        """Optimize processing based on performance metrics"""
        if len(self.processing_times) < 10:
            return  # Not enough data to optimize

        avg_time = sum(self.processing_times) / len(self.processing_times)
        max_time = max(self.processing_times)

        # If processing is consistently slow, log a warning
        if avg_time > 0.1:  # 100ms threshold
            logger.warning(f"Engine {self.name} has slow average processing time: {avg_time:.3f}s")
    
    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name


class TrendEngineAdapter(BaseEngineAdapter):
    """Infrastructure adapter for trend analysis engine"""
    
    def __init__(self):
        super().__init__("TrendEngine")
        self.lookback_period = 50
        self.price_history: List[float] = []
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through trend analysis"""
        logger.info(f"TrendEngine processing signal for {signal.symbol.value}")
        return signal  # In this implementation we return the signal unchanged
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data for trend analysis"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback_period * 3:
                self.price_history.pop(0)  # Keep only recent data


class VolatilityEngineAdapter(BaseEngineAdapter):
    """Infrastructure adapter for volatility analysis engine"""
    
    def __init__(self):
        super().__init__("VolatilityEngine")
        self.lookback_period = 20
        self.price_history: List[float] = []
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through volatility analysis"""
        logger.info(f"VolatilityEngine processing signal for {signal.symbol.value}")
        return signal  # In this implementation we return the signal unchanged
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with market data for volatility analysis"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback_period * 4:
                self.price_history.pop(0)  # Keep only recent data


class LiquidityEngineAdapter(BaseEngineAdapter):
    """Infrastructure adapter for liquidity analysis engine"""
    
    def __init__(self):
        super().__init__("LiquidityEngine")
        self.lookback_period = 10
        self.bids: List[tuple] = []  # (price, volume)
        self.asks: List[tuple] = []  # (price, volume)
        self.spread_history: List[float] = []
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through liquidity analysis"""
        logger.info(f"LiquidityEngine processing signal for {signal.symbol.value}")
        return signal  # In this implementation we return the signal unchanged
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with market data for liquidity analysis"""
        if 'bids' in data and 'asks' in data:
            # Update order book data
            self.bids = [(float(price), float(vol)) for price, vol in data['bids'][:10]]
            self.asks = [(float(price), float(vol)) for price, vol in data['asks'][:10]]
            
            # Calculate spread
            if self.bids and self.asks:
                best_bid = self.bids[0][0] if self.bids else 0
                best_ask = self.asks[0][0] if self.asks else 0
                if best_bid > 0:
                    spread = (best_ask - best_bid) / best_bid
                    self.spread_history.append(spread)
                    if len(self.spread_history) > self.lookback_period * 3:
                        self.spread_history.pop(0)


class OrderFlowEngineAdapter(BaseEngineAdapter):
    """Infrastructure adapter for order flow analysis engine"""
    
    def __init__(self):
        super().__init__("OrderFlowEngine")
        self.lookback_period = 20
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through order flow analysis"""
        logger.info(f"OrderFlowEngine processing signal for {signal.symbol.value}")
        return signal  # In this implementation we return the signal unchanged
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with market data for order flow analysis"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback_period * 3:
                self.price_history.pop(0)  # Keep only recent data


class RegimeEngineAdapter(BaseEngineAdapter):
    """Infrastructure adapter for market regime detection engine"""
    
    def __init__(self):
        super().__init__("RegimeEngine")
        self.lookback_period = 30
        self.price_history: List[float] = []
        self.trend_regime = "neutral"
        self.volatility_regime = "normal"
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal through regime analysis"""
        logger.info(f"RegimeEngine processing signal for {signal.symbol.value}")
        return signal  # In this implementation we return the signal unchanged
    
    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with market data for regime detection"""
        if 'close' in data:
            self.price_history.append(float(data['close']))
            if len(self.price_history) > self.lookback_period * 4:
                self.price_history.pop(0)  # Keep only recent data
    
    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process this signal"""
        return len(self.price_history) >= 5  # Need at least 5 data points


__all__ = [
    'BaseEngineAdapter',
    'TrendEngineAdapter', 
    'VolatilityEngineAdapter',
    'LiquidityEngineAdapter',
    'OrderFlowEngineAdapter',
    'RegimeEngineAdapter'
]