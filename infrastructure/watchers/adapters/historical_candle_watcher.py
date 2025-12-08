"""
Infrastructure implementation of historical candle watcher following hexagonal architecture.
This is inspired by the temp-sample-features historical_candle_watcher but adapted to the current hexagonal architecture.
"""
from typing import List, Dict, Any, Optional
import threading
import time
from datetime import datetime

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
        self.timeframe = timeframe
        self.speed = speed  # 1.0 = real-time, higher = faster
        self.symbols = {symbol}
        self.running = False
        self.thread = None
        self.current_index = 0
        self.historical_candles = []
        self.current_candle = None

    def analyze(self, symbol: Symbol = None):
        """Analyze current historical candle data"""
        if not self.historical_candles or self.current_index >= len(self.historical_candles):
            logger.debug(f"No historical data or reached end in HistoricalCandleWatcher {self.name}")
            return None

        try:
            current_candle = self.historical_candles[self.current_index - 1] if self.current_index > 0 else self.historical_candles[0]
            
            # Simple analysis for demonstration - in real implementation would be more sophisticated
            open_price = float(current_candle.get('open', 0))
            close_price = float(current_candle.get('close', 0))
            high_price = float(current_candle.get('high', 0))
            low_price = float(current_candle.get('low', 0))
            
            if open_price != 0:
                change_pct = (close_price - open_price) / open_price
            else:
                change_pct = 0

            # Determine signal based on candle pattern and change direction
            if change_pct > 0.02:  # 2% up
                signal_type = SignalType.BUY
                confidence = Percentage(Decimal('0.8'))
                score = 0.8
            elif change_pct < -0.02:  # 2% down
                signal_type = SignalType.SELL
                confidence = Percentage(Decimal('0.8'))
                score = -0.8
            elif abs(change_pct) < 0.005:  # Very small change
                signal_type = SignalType.NEUTRAL
                confidence = Percentage(Decimal('0.3'))
                score = 0.0
            else:  # Somewhat neutral
                signal_type = SignalType.NEUTRAL
                confidence = Percentage(Decimal('0.5'))
                score = 0.1 if change_pct > 0 else -0.1

            historical_signal = Signal(
                symbol=symbol or self.symbol,
                signal_type=signal_type,
                confidence=confidence,
                score=score,
                strategy_name=f"HistoricalCandleWatcher_{self.name}",
                timestamp=datetime.now(),
                metadata={
                    'candle_analysis': {
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'change_pct': change_pct,
                        'timeframe': self.timeframe
                    },
                    'candle_data': current_candle
                }
            )
            
            return historical_signal
        except Exception as e:
            logger.error(f"Error in HistoricalCandleWatcher {self.name} analysis: {e}")
            return None

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