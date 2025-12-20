"""
Infrastructure implementation of historical candle watcher following hexagonal architecture.
This is inspired by the temp-sample-features historical_candle_watcher but adapted to the current hexagonal architecture.
"""
from typing import List, Dict, Any, Optional
import threading
import time
from datetime import datetime
import os

from domain.ports.watcher_ports import WatcherPort
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from decimal import Decimal


class HistoricalCandleWatcherAdapter(WatcherPort):
    """
    Infrastructure implementation of historical candle watcher following hexagonal architecture.
    Useful for backtesting and analyzing historical data sequentially.
    """

    def __init__(self, name: str, symbol: str, data_provider, timeframe: str = "1m", speed: float = 1.0):
        self.name = name
        self.symbol = Symbol(symbol)
        self.data_provider = data_provider  # Could be a CSV loader, API, etc.

        # Configuration from environment with defaults - enabled by default
        self.enabled = os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true'

        # Only set logger if enabled, otherwise use mock logger
        if self.enabled:
            from shared.logger import logger as self_logger
            self.logger = self_logger
        else:
            # Create a mock logger that doesn't log anything when disabled
            class MockLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = MockLogger()

        self.timeframe = timeframe
        self.speed = speed  # 1.0 = real-time, higher = faster
        self.symbols = {symbol}
        self.running = False
        self.thread = None
        self.current_index = 0
        self.historical_candles = []
        self.current_candle = None

        # Pattern detection parameters
        self.min_pattern_confirmation_bars = 3  # Minimum bars for pattern confirmation
        self.max_patterns_to_detect = 5  # Limit to justified set of patterns
        self.pattern_history = []  # Track detected patterns for confirmation

    def analyze(self, symbol: Symbol = None):
        """Analyze current historical candle data with strict pattern detection rules"""
        if not self.enabled:
            return None

        if not self.historical_candles or self.current_index < self.min_pattern_confirmation_bars:
            logger.debug(f"Not enough historical data for pattern confirmation in HistoricalCandleWatcher {self.name}")
            return None

        try:
            # Get the current and previous candles for pattern analysis
            if self.current_index >= len(self.historical_candles):
                return None

            # Use multiple candles for pattern confirmation (no single-candle signals)
            candles_to_analyze = self.get_candles_for_analysis(self.current_index)

            if len(candles_to_analyze) < self.min_pattern_confirmation_bars:
                return None

            # Detect only a small, justified set of patterns
            pattern_detected, confidence, score, pattern_type = self.detect_justified_patterns(candles_to_analyze)

            if not pattern_detected:
                # Return HOLD when no confirmed pattern is detected
                return Signal(
                    symbol=symbol or self.symbol,
                    signal_type=SignalType.HOLD,
                    confidence=Percentage(Decimal('0.2')),
                    score=0.0,
                    strategy_name=f"HistoricalCandleWatcher_{self.name}",
                    timestamp=datetime.now(),
                    metadata={
                        'candle_analysis': {
                            'timeframe': self.timeframe,
                            'candles_analyzed': len(candles_to_analyze),
                            'pattern_detected': False,
                            'explanation': 'No confirmed patterns detected in recent candles'
                        }
                    }
                )

            # Determine signal based on confirmed pattern
            signal_type = self.determine_signal_from_pattern(pattern_type)

            historical_signal = Signal(
                symbol=symbol or self.symbol,
                signal_type=signal_type,
                confidence=Percentage(confidence),
                score=score,
                strategy_name=f"HistoricalCandleWatcher_{self.name}",
                timestamp=datetime.now(),
                metadata={
                    'candle_analysis': {
                        'timeframe': self.timeframe,
                        'candles_analyzed': len(candles_to_analyze),
                        'pattern_type': pattern_type,
                        'pattern_detected': True,
                        'explanation': f"Confirmed {pattern_type} pattern detected with strict confirmation rules"
                    },
                    'candle_data': candles_to_analyze[-1]  # Include the most recent candle data
                }
            )

            return historical_signal
        except Exception as e:
            logger.error(f"Error in HistoricalCandleWatcher {self.name} analysis: {e}")
            return None

    def get_candles_for_analysis(self, index: int) -> List[Dict]:
        """Get candles for pattern analysis with lookback window"""
        start_idx = max(0, index - self.min_pattern_confirmation_bars)
        return self.historical_candles[start_idx:index]

    def detect_justified_patterns(self, candles: List[Dict]) -> tuple:
        """Detect only a small, justified set of patterns with strict confirmation rules"""
        if len(candles) < self.min_pattern_confirmation_bars:
            return False, Decimal('0.0'), 0.0, "none"

        # Pattern 1: Confirmed trend continuation (at least 3 candles in same direction)
        trend_continuation = self.detect_trend_continuation(candles)
        if trend_continuation[0]:
            return trend_continuation

        # Pattern 2: Potential reversal after strong move (at least 3 candles with confirmation)
        reversal_pattern = self.detect_reversal_pattern(candles)
        if reversal_pattern[0]:
            return reversal_pattern

        # Pattern 3: Range bound (at least 3 candles within tight range)
        range_bound = self.detect_range_bound(candles)
        if range_bound[0]:
            return range_bound

        # No significant pattern detected
        return False, Decimal('0.0'), 0.0, "none"

    def detect_trend_continuation(self, candles: List[Dict]) -> tuple:
        """Detect trend continuation with strict confirmation"""
        if len(candles) < 3:
            return False, Decimal('0.0'), 0.0, "none"

        # Check if last 3 candles are in same direction with increasing momentum
        closes = [float(candle.get('close', 0)) for candle in candles]

        # Check if all closes are in the same direction (uptrend or downtrend)
        uptrend = all(closes[i] > closes[i-1] for i in range(1, len(closes)))
        downtrend = all(closes[i] < closes[i-1] for i in range(1, len(closes)))

        if uptrend:
            return True, Decimal('0.7'), 0.6, "uptrend_continuation"
        elif downtrend:
            return True, Decimal('0.7'), -0.6, "downtrend_continuation"

        return False, Decimal('0.0'), 0.0, "none"

    def detect_reversal_pattern(self, candles: List[Dict]) -> tuple:
        """Detect potential reversal pattern with strict confirmation"""
        if len(candles) < 3:
            return False, Decimal('0.0'), 0.0, "none"

        # Simple reversal detection: strong move followed by counter-move
        closes = [float(candle.get('close', 0)) for candle in candles]

        # Check for reversal: strong move in one direction followed by move in opposite direction
        if len(candles) >= 3:
            first_to_last_change = (closes[-1] - closes[0]) / closes[0] if closes[0] != 0 else 0
            middle_change = (closes[1] - closes[0]) / closes[0] if closes[0] != 0 else 0

            # If first two candles show strong move and last candle reverses
            if abs(middle_change) > 0.02 and (middle_change > 0) != (first_to_last_change > 0):
                direction = "reversal_to_down" if first_to_last_change < 0 else "reversal_to_up"
                score = -0.5 if first_to_last_change < 0 else 0.5
                return True, Decimal('0.6'), score, direction

        return False, Decimal('0.0'), 0.0, "none"

    def detect_range_bound(self, candles: List[Dict]) -> tuple:
        """Detect range-bound conditions with strict confirmation"""
        if len(candles) < 3:
            return False, Decimal('0.0'), 0.0, "none"

        highs = [float(candle.get('high', 0)) for candle in candles]
        lows = [float(candle.get('low', 0)) for candle in candles]

        # Calculate average range
        avg_range = sum(h - l for h, l in zip(highs, lows)) / len(candles) if candles else 0
        max_high = max(highs)
        min_low = min(lows)
        total_range = max_high - min_low

        # Check if candles are relatively range-bound (total range not much larger than average individual range)
        if total_range < avg_range * 2.5 and len(candles) >= 3:
            # Range bound detected
            return True, Decimal('0.5'), 0.0, "range_bound"

        return False, Decimal('0.0'), 0.0, "none"

    def determine_signal_from_pattern(self, pattern_type: str) -> SignalType:
        """Determine signal type based on detected pattern"""
        if pattern_type in ["uptrend_continuation"]:
            return SignalType.BUY
        elif pattern_type in ["downtrend_continuation"]:
            return SignalType.SELL
        elif pattern_type in ["reversal_to_up"]:
            return SignalType.BUY
        elif pattern_type in ["reversal_to_down"]:
            return SignalType.SELL
        else:
            return SignalType.HOLD

    def start(self):
        """Start the historical candle watcher"""
        if self.data_provider:
            # Load historical data
            try:
                self.historical_candles = self.data_provider.load_candles(str(self.symbol), self.timeframe)
            except AttributeError:
                # If data_provider doesn't have load_candles method, try other approaches
                try:
                    # Assume it's a market data service
                    self.historical_candles = self.data_provider.get_historical_data(self.symbol, '1d')  # Simplified
                except:
                    logger.warning(f"Could not load historical data in HistoricalCandleWatcher {self.name}")
                    self.historical_candles = []
        
        self.running = True
        self.thread = threading.Thread(target=self._historical_loop, daemon=True)
        self.thread.start()
        logger.info(f"HistoricalCandleWatcher {self.name} started for {self.symbol.value}")

    def stop(self):
        """Stop the historical candle watcher"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info(f"HistoricalCandleWatcher {self.name} stopped")

    def is_running(self) -> bool:
        """Check if the watcher is running"""
        return self.running

    def update_data(self, data: Dict[str, Any]):
        """Update with new data (not typically used in historical backtesting)"""
        # For historical watcher, this is less relevant since we're processing stored data
        pass

    def subscribe(self, symbol: Symbol):
        """Subscribe to a symbol"""
        self.symbols.add(str(symbol.value))

    def unsubscribe(self, symbol: Symbol):
        """Unsubscribe from a symbol"""
        self.symbols.discard(str(symbol.value))

    def get_watcher_name(self) -> str:
        """Get the name of the watcher"""
        return self.name

    def _historical_loop(self):
        """Main historical data processing loop"""
        while self.running and self.current_index < len(self.historical_candles):
            try:
                # Process current candle
                self.current_candle = self.historical_candles[self.current_index]
                self.current_index += 1
                
                # Sleep based on configured speed
                sleep_time = (1.0 / self.speed) if self.speed > 0 else 1.0
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Error in HistoricalCandleWatcher loop: {e}")
                time.sleep(1)  # Wait before continuing after error