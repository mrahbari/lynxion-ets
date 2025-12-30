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

            # Analyze tick data for patterns and momentum shifts
            tick_signal = self._analyze_tick_data(symbol or self.symbol, current_price)

            if tick_signal is None:
                # If no clear signal from tick analysis, return HOLD with low confidence
                tick_signal = Signal(
                    symbol=symbol or self.symbol,
                    signal_type=SignalType.HOLD,
                    confidence=Percentage(Decimal('0.2')),
                    score=0.0,
                    strategy_name=f"TickWatcher_{self.name}",
                    timestamp=datetime.now(),
                    metadata={
                        'tick_analysis': 'insufficient_data',
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

    def _analyze_tick_data(self, symbol: Symbol, current_price: float) -> Optional[Signal]:
        """Analyze tick data for momentum shifts, volume imbalances, and patterns"""
        if len(self.tick_cache) < 10:  # Need sufficient tick data for analysis
            return None

        # Extract recent tick data
        recent_ticks = self.tick_cache[-20:] if len(self.tick_cache) >= 20 else self.tick_cache

        # Calculate price momentum from recent ticks
        prices = [tick.get('price', tick.get('close', tick.get('last', current_price)))
                  for tick in recent_ticks if 'price' in tick or 'close' in tick or 'last' in tick]

        if len(prices) < 5:
            return None

        # Calculate recent momentum (direction and strength)
        recent_momentum = (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0

        # Calculate volatility from recent ticks
        import numpy as np
        price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] if prices[i-1] != 0 else 0
                         for i in range(1, len(prices))]
        volatility = np.mean(price_changes) if price_changes else 0

        # Calculate volume metrics if available
        volumes = [tick.get('volume', tick.get('qty', 0)) for tick in recent_ticks]
        avg_volume = np.mean(volumes) if volumes else 0
        current_volume = volumes[-1] if volumes else 0
        volume_spike = current_volume / avg_volume if avg_volume > 0 else 0

        # Determine signal based on momentum, volatility, and volume
        signal_type = SignalType.HOLD
        confidence = 0.3
        score = 0.0

        # Strong momentum with volume confirmation
        if abs(recent_momentum) > 0.005 and volume_spike > 1.5:  # 0.5% momentum + 50% volume spike
            if recent_momentum > 0:
                signal_type = SignalType.BUY
                confidence = min(0.9, abs(recent_momentum) * 100 + volume_spike * 0.1)
            else:
                signal_type = SignalType.SELL
                confidence = min(0.9, abs(recent_momentum) * 100 + volume_spike * 0.1)
        # Moderate momentum
        elif abs(recent_momentum) > 0.002:  # 0.2% momentum
            if recent_momentum > 0:
                signal_type = SignalType.BUY
                confidence = min(0.7, abs(recent_momentum) * 100)
            else:
                signal_type = SignalType.SELL
                confidence = min(0.7, abs(recent_momentum) * 100)
        # High volatility without clear direction (potential reversal zone)
        elif volatility > 0.008:  # High volatility
            # Look for signs of exhaustion or reversal
            if recent_momentum > 0 and len(prices) > 10:
                # Check if momentum is decreasing (sign of potential reversal)
                earlier_momentum = (prices[5] - prices[0]) / prices[0] if prices[0] != 0 else 0
                if earlier_momentum > abs(recent_momentum):  # Earlier momentum was stronger
                    signal_type = SignalType.SELL  # Potential reversal from high momentum
                    confidence = 0.6
            elif recent_momentum < 0 and len(prices) > 10:
                earlier_momentum = (prices[5] - prices[0]) / prices[0] if prices[0] != 0 else 0
                if earlier_momentum < recent_momentum:  # Earlier momentum was stronger negative
                    signal_type = SignalType.BUY  # Potential reversal from low momentum
                    confidence = 0.6

        if signal_type != SignalType.HOLD:
            score = recent_momentum  # Use momentum as score
            return Signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=Percentage(Decimal(str(confidence))),
                score=score,
                strategy_name=f"TickWatcher_{self.name}",
                timestamp=datetime.now(),
                metadata={
                    'tick_analysis': {
                        'momentum': recent_momentum,
                        'volatility': volatility,
                        'volume_spike': volume_spike,
                        'avg_volume': avg_volume,
                        'ticks_analyzed': len(recent_ticks)
                    },
                    'last_price': current_price,
                    'tick_volume': len(self.tick_cache)
                }
            )

        return None  # No clear signal