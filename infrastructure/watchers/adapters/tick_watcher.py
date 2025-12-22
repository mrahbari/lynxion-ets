"""
Infrastructure implementation of tick watcher following hexagonal architecture.
This is inspired by the temp-sample-features tick_watcher but adapted to the current hexagonal architecture.
"""
from typing import List, Dict, Any, Optional
import os
import threading
import time
from datetime import datetime

from domain.ports.watcher_ports import WatcherPort
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from decimal import Decimal


class TickWatcherAdapter(WatcherPort):
    """
    Infrastructure implementation of tick watcher following hexagonal architecture.
    Processes tick-level data for high-frequency strategies.
    """
    
    def __init__(self, name: str, symbol: str, broker_service, target_broker: str = None):
        self.name = name
        self.symbol = Symbol(symbol)
        self.broker_service = broker_service
        self.target_broker = target_broker
        self.symbols = {symbol}
        self.running = False
        self.thread = None
        self.last_tick_data = {}
        self.tick_cache = []

        # Configuration from environment with defaults - enabled by default
        self.enabled = os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true'

        # Only set logger if enabled, otherwise use mock logger
        if self.enabled:
            self.logger = logger
        else:
            # Create a mock logger that doesn't log anything when disabled
            class MockLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = MockLogger()

    def analyze(self, symbol: Symbol = None):
        """Analyze tick data with proper enablement check"""
        # Check if enabled first
        if not self.enabled:
            return None

        if not self.running:
            self.logger.warning(f"TickWatcher {self.name} not running, cannot analyze")
            return None

        # In a real implementation, this would analyze tick data for patterns,
        # momentum shifts, volume imbalances, etc.

        # For now, return a neutral signal as placeholder
        try:
            current_price = self._get_current_price(symbol or self.symbol)
            if current_price is None:
                return None

            # Placeholder logic - in real implementation this would analyze tick data
            tick_signal = Signal(
                symbol=symbol or self.symbol,
                signal_type=SignalType.NEUTRAL,
                confidence=Percentage(Decimal('0.5')),
                score=0.0,
                strategy_name=f"TickWatcher_{self.name}",
                timestamp=datetime.now(),
                metadata={
                    'tick_analysis': 'placeholder',
                    'last_price': current_price,
                    'tick_volume': len(self.tick_cache) if self.tick_cache else 0
                }
            )

            return tick_signal
        except Exception as e:
            self.logger.error(f"Error in TickWatcher {self.name} analysis: {e}")
            return None

    def start(self):
        """Start the tick watcher"""
        self.running = True
        self.thread = threading.Thread(target=self._tick_loop, daemon=True)
        self.thread.start()
        logger.info(f"TickWatcher {self.name} started for {self.symbol.value}")

    def stop(self):
        """Stop the tick watcher"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info(f"TickWatcher {self.name} stopped")

    def is_running(self) -> bool:
        """Check if the watcher is running"""
        return self.running

    def update_data(self, data: Dict[str, Any]):
        """Update with new tick data"""
        if 'symbol' in data and data['symbol'] == self.symbol.value:
            self.last_tick_data = data
            self.tick_cache.append(data)
            # Keep only recent ticks to avoid memory issues
            if len(self.tick_cache) > 1000:
                self.tick_cache = self.tick_cache[-500:]

    def subscribe(self, symbol: Symbol):
        """Subscribe to a symbol"""
        self.symbols.add(str(symbol.value))

    def unsubscribe(self, symbol: Symbol):
        """Unsubscribe from a symbol"""
        self.symbols.discard(str(symbol.value))

    def get_watcher_name(self) -> str:
        """Get the name of the watcher"""
        return self.name

    def _tick_loop(self):
        """Main tick processing loop"""
        while self.running:
            try:
                # In a real implementation, this would fetch tick data from broker
                # and process it in real-time
                time.sleep(0.1)  # Simulate tick processing interval
            except Exception as e:
                logger.error(f"Error in TickWatcher loop: {e}")
                time.sleep(1)  # Wait before continuing after error

    def _get_current_price(self, symbol: Symbol) -> Optional[float]:
        """Get current price for symbol from broker"""
        try:
            # Use broker service to get current market data
            # This is a simplified approach - in real implementation, would use
            # appropriate broker API methods
            from infrastructure.brokers.broker_manager import BrokerManager
            if hasattr(self.broker_service, 'get_price'):
                return self.broker_service.get_price(symbol)
            else:
                # Fallback to a generic method
                return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol.value}: {e}")
            return None