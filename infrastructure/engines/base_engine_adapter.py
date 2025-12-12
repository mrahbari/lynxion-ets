"""
Base class for engine adapters with common functionality.
"""
from typing import List, Dict, Any
import numpy as np
import time
from datetime import datetime
from domain.entities.trading_entities import Signal
from domain.value_objects import Percentage
from domain.ports.engine_ports import EnginePort
from shared.logger import logger
from decimal import Decimal


class BaseEngineAdapter(EnginePort):
    """Base class for all engine adapters with common functionality"""

    def __init__(self, name: str):
        self.name = name
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.high_history: List[float] = []
        self.low_history: List[float] = []
        self.max_history_length = 500  # Maximum history to keep

        # Performance monitoring
        self.processing_times: List[float] = []  # Track processing times
        self.signals_processed: int = 0  # Total signals processed
        self.signals_improved: int = 0  # Signals where confidence was improved
        self.signals_worsened: int = 0  # Signals where confidence was reduced
        self.last_processed_timestamp: float = 0  # Track when last processed

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update engine with new market data - common implementation"""
        try:
            if 'close' in data:
                self.price_history.append(float(data['close']))
                if len(self.price_history) > self.max_history_length:
                    self.price_history.pop(0)
            
            if 'volume' in data:
                self.volume_history.append(float(data['volume']))
                if len(self.volume_history) > self.max_history_length:
                    self.volume_history.pop(0)
            
            if 'high' in data:
                self.high_history.append(float(data['high']))
                if len(self.high_history) > self.max_history_length:
                    self.high_history.pop(0)
            
            if 'low' in data:
                self.low_history.append(float(data['low']))
                if len(self.low_history) > self.max_history_length:
                    self.low_history.pop(0)
        except Exception as e:
            logger.error(f"Error updating {self.name} with market data: {e}")

    def calculate_volatility(self, prices: List[float], period: int = 20) -> float:
        """Calculate volatility over a given period"""
        if len(prices) < 2:
            return 0.0
        
        recent_prices = prices[-min(len(prices), period):]
        returns = np.diff(recent_prices) / np.array(recent_prices[:-1])
        if len(returns) > 0:
            return float(np.std(returns))
        return 0.0

    def calculate_trend(self, prices: List[float], period: int = 20) -> float:
        """Calculate trend using linear regression"""
        if len(prices) < 5:
            return 0.0
            
        recent_prices = prices[-min(len(prices), period):]
        x = np.arange(len(recent_prices))
        
        if len(x) > 1:
            slope = (len(x) * np.sum(x * recent_prices) - np.sum(x) * np.sum(recent_prices)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)
                    
            avg_price = np.mean(recent_prices)
            return slope / avg_price if avg_price != 0 else 0.0
        
        return 0.0

    def calculate_atr(self, high_prices: List[float], low_prices: List[float], 
                     close_prices: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(high_prices) < 2 or len(low_prices) < 2 or len(close_prices) < 2:
            return 0.0

        true_ranges = []
        for i in range(1, min(len(high_prices), len(low_prices), len(close_prices))):
            high_low = high_prices[i] - low_prices[i]
            high_close = abs(high_prices[i] - close_prices[i-1])
            low_close = abs(low_prices[i] - close_prices[i-1])
            
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)

        recent_tr = true_ranges[-min(len(true_ranges), period):]
        if recent_tr:
            return float(np.mean(recent_tr))
        
        return 0.0

    def record_performance(self,
                          processing_time: float,
                          original_signal: Signal,
                          processed_signal: Signal):
        """Record performance metrics for the processing operation"""
        self.signals_processed += 1
        self.processing_times.append(processing_time)

        # Track if the signal confidence was improved or worsened
        original_conf = float(original_signal.confidence.value)
        processed_conf = float(processed_signal.confidence.value)

        if processed_conf > original_conf:
            self.signals_improved += 1
        elif processed_conf < original_conf:
            self.signals_worsened += 1

        self.last_processed_timestamp = time.time()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the engine"""
        total_signals = self.signals_processed
        if total_signals == 0:
            return {
                'engine_name': self.name,
                'signals_processed': 0,
                'avg_processing_time': 0,
                'min_processing_time': 0,
                'max_processing_time': 0,
                'signals_improved_ratio': 0,
                'signals_worsened_ratio': 0,
                'last_processed': None
            }

        avg_time = sum(self.processing_times) / len(self.processing_times)
        min_time = min(self.processing_times)
        max_time = max(self.processing_times) if self.processing_times else 0

        return {
            'engine_name': self.name,
            'signals_processed': total_signals,
            'avg_processing_time': avg_time,
            'min_processing_time': min_time,
            'max_processing_time': max_time,
            'signals_improved_ratio': self.signals_improved / total_signals if total_signals > 0 else 0,
            'signals_worsened_ratio': self.signals_worsened / total_signals if total_signals > 0 else 0,
            'last_processed': datetime.fromtimestamp(self.last_processed_timestamp) if self.last_processed_timestamp > 0 else None
        }

    def adjust_confidence(self, signal: Signal, adjustment_factor: float) -> Signal:
        """Adjust signal confidence by a factor"""
        new_confidence_value = signal.confidence.value * Decimal(str(adjustment_factor))
        new_confidence = Percentage(
            max(Decimal('0.0'), min(Decimal('1.0'), new_confidence_value))
        )

        return Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=signal.score * adjustment_factor,
            strategy_name=signal.strategy_name,
            timestamp=signal.timestamp,
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                f'{self.name.lower()}_adjusted': True
            }
        )

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal - base implementation"""
        return True

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name