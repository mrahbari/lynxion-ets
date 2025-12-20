from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np
from typing import Dict, List, Optional
import threading
import queue
import os


class OrderFlowWSWatcher(BaseWatcher):
    """Order Flow Watcher using WebSocket - analyzes order book dynamics"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, depth_levels: int = 10):
        super().__init__(name, symbol, broker_service, target_broker)

        # Configuration from environment with defaults
        self.enabled = os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'true').lower() == 'true'

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

        self.depth_levels = depth_levels

        # Order book data
        self.bids = {}  # price -> quantity
        self.asks = {}  # price -> quantity
        self.bid_volume_total = 0
        self.ask_volume_total = 0

        # Order flow metrics
        self.order_flow_imbalance = 0
        self.aggressive_buy_volume = 0
        self.aggressive_sell_volume = 0
        self.order_flow_history = []
        self.max_history = 100

        # Temporal confirmation parameters
        self.temporal_confirmation_windows = 3  # Number of consecutive windows needed
        self.temporal_counter = 0  # Counter for consecutive signals
        self.last_signal_direction = 0  # Track last signal direction for temporal confirmation

        # Signal thresholds
        self.imbalance_threshold = 0.15  # Increased threshold to reduce noise
        self.volume_spike_threshold = 2.5  # Increased threshold to reduce noise
        self.persistence_threshold = 0.6  # Minimum persistence ratio for signal

        # Cooldown mechanism
        self.signal_cooldown = 0
        self.max_cooldown = 10  # Cooldown after signal emission

        # WebSocket connection (simulated)
        self.ws_connected = False
        self.data_queue = queue.Queue()

    def update_data(self, data: Dict):
        """Update with new market data (order book updates)"""
        if not self.enabled:
            return

        # Update order book if new data is provided
        if 'bids' in data and 'asks' in data:
            self.bids = {float(price): float(vol) for price, vol in data['bids']}
            self.asks = {float(price): float(vol) for price, vol in data['asks']}

            # Calculate totals
            self.bid_volume_total = sum(self.bids.values())
            self.ask_volume_total = sum(self.asks.values())

            # Calculate order flow metrics
            self.calculate_order_flow_metrics()

        # Process any queued WebSocket updates
        self.process_websocket_queue()

    def calculate_order_flow_metrics(self):
        """Calculate order flow metrics with temporal context"""
        if self.bid_volume_total + self.ask_volume_total == 0:
            self.order_flow_imbalance = 0
            return

        # Calculate order flow imbalance (bids vs asks)
        self.order_flow_imbalance = (self.bid_volume_total - self.ask_volume_total) / (self.bid_volume_total + self.ask_volume_total)

        # Add to history with timestamp
        self.order_flow_history.append({
            'timestamp': datetime.now(),
            'imbalance': self.order_flow_imbalance,
            'bid_total': self.bid_volume_total,
            'ask_total': self.ask_volume_total,
            'spread': (min(self.asks.keys()) - max(self.bids.keys())) if self.bids and self.asks else 0
        })

        # Keep history to max length
        if len(self.order_flow_history) > self.max_history:
            self.order_flow_history.pop(0)

    def process_websocket_queue(self):
        """Process any WebSocket data in the queue"""
        # This would handle actual WebSocket messages in a real implementation
        while not self.data_queue.empty():
            try:
                data = self.data_queue.get_nowait()
                # Process the WebSocket data
                self.update_data(data)
            except queue.Empty:
                break

    def analyze(self, symbol: Symbol) -> Signal:
        """Analyze order flow and return a signal"""
        if not self.enabled:
            return None

        if not self.order_flow_history or len(self.order_flow_history) < 5:
            return None

        # Apply cooldown
        if self.signal_cooldown > 0:
            self.signal_cooldown -= 1
            # Return HOLD during cooldown with low confidence
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                confidence=0.1,
                score=0.0,
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={
                    'explanation': 'Order flow watcher in cooldown period',
                    'imbalance': self.order_flow_imbalance
                }
            )

        # Separate imbalance detection from persistence validation
        imbalance_detected = self.detect_imbalance()
        persistence_validated = self.validate_persistence()

        # Only emit signal if both detection and persistence are validated
        if not (imbalance_detected and persistence_validated):
            # Return HOLD when no significant persistent imbalance detected
            return Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                confidence=0.3,
                score=0.0,
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={
                    'explanation': f'No persistent imbalance detected. Imbalance: {self.order_flow_imbalance:.3f}',
                    'imbalance_detected': imbalance_detected,
                    'persistence_validated': persistence_validated
                }
            )

        # Calculate signal parameters
        avg_imbalance = np.mean([d['imbalance'] for d in self.order_flow_history[-3:]])

        # Determine signal type based on validated persistent imbalance
        if avg_imbalance > self.imbalance_threshold:
            signal_type = SignalType.BUY
            confidence = min(1.0, abs(avg_imbalance) / self.imbalance_threshold)
        elif avg_imbalance < -self.imbalance_threshold:
            signal_type = SignalType.SELL
            confidence = min(1.0, abs(avg_imbalance) / self.imbalance_threshold)
        else:
            signal_type = SignalType.HOLD
            confidence = 0.3

        # Apply volume confirmation
        volume_confirmation = self.check_volume_confirmation()
        if volume_confirmation != 0:
            confidence = min(1.0, confidence * 1.2)  # Boost confidence with volume confirmation

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=avg_imbalance,
            strategy=self.name,
            timestamp=datetime.now(),
            metadata={
                'explanation': f'Sustained bid imbalance over {self.temporal_confirmation_windows} windows with ratio {avg_imbalance:.3f}',
                'imbalance_detected': imbalance_detected,
                'persistence_validated': persistence_validated,
                'volume_confirmation': volume_confirmation,
                'avg_imbalance': avg_imbalance,
                'temporal_windows': self.temporal_confirmation_windows
            }
        )

        # Update last signal if it's different enough and activate cooldown
        if self.should_emit_signal(signal):
            self.last_signal = signal
            self.signal_cooldown = self.max_cooldown  # Activate cooldown
            logger.debug(f"OrderFlowWSWatcher {self.name} generated signal: {signal_type} with imbalance {avg_imbalance:.3f}")

        return signal

    def detect_imbalance(self) -> bool:
        """Separate function to detect order flow imbalance"""
        if not self.order_flow_history or len(self.order_flow_history) < 3:
            return False

        # Check the most recent imbalance values
        recent_imbalances = [d['imbalance'] for d in self.order_flow_history[-3:]]

        # Check if recent imbalances exceed threshold in same direction
        positive_imbalance = all(imb > self.imbalance_threshold for imb in recent_imbalances)
        negative_imbalance = all(imb < -self.imbalance_threshold for imb in recent_imbalances)

        return positive_imbalance or negative_imbalance

    def validate_persistence(self) -> bool:
        """Validate that the detected imbalance is persistent, not transient"""
        if not self.order_flow_history or len(self.order_flow_history) < self.temporal_confirmation_windows:
            return False

        # Get the most recent windows
        recent_data = self.order_flow_history[-self.temporal_confirmation_windows:]

        # Calculate persistence ratio
        imbalances = [d['imbalance'] for d in recent_data]

        # Check if imbalances are consistently in the same direction
        positive_count = sum(1 for imb in imbalances if imb > self.imbalance_threshold)
        negative_count = sum(1 for imb in imbalances if imb < -self.imbalance_threshold)

        # Persistence is validated if majority of windows show same direction
        max_count = max(positive_count, negative_count)
        persistence_ratio = max_count / self.temporal_confirmation_windows

        return persistence_ratio >= self.persistence_threshold

    def check_volume_confirmation(self) -> int:
        """Check if volume confirms the directional bias"""
        if not self.order_flow_history or len(self.order_flow_history) < 10:
            return 0

        # Compare recent volumes to historical average
        recent_data = self.order_flow_history[-3:]  # Use fewer for more responsive confirmation

        # Calculate historical average (excluding recent)
        historical_data = self.order_flow_history[:-3] if len(self.order_flow_history) > 3 else self.order_flow_history
        if not historical_data:
            return 0

        historical_avg_bid = np.mean([d['bid_total'] for d in historical_data])
        historical_avg_ask = np.mean([d['ask_total'] for d in historical_data])

        recent_avg_bid = np.mean([d['bid_total'] for d in recent_data])
        recent_avg_ask = np.mean([d['ask_total'] for d in recent_data])

        # Check which side has increased volume relative to average
        bid_volume_spike = recent_avg_bid / historical_avg_bid if historical_avg_bid > 0 else 1
        ask_volume_spike = recent_avg_ask / historical_avg_ask if historical_avg_ask > 0 else 1

        # Return +1 for bullish confirmation, -1 for bearish, 0 for none
        current_imbalance = self.order_flow_history[-1]['imbalance'] if self.order_flow_history else 0

        if current_imbalance > 0 and bid_volume_spike > self.volume_spike_threshold:
            return 1  # Bullish confirmation
        elif current_imbalance < 0 and ask_volume_spike > self.volume_spike_threshold:
            return -1  # Bearish confirmation
        else:
            return 0  # No strong confirmation

    def get_order_book_snapshot(self) -> Dict:
        """Get current order book snapshot"""
        return {
            'bids': dict(self.bids),
            'asks': dict(self.asks),
            'bid_total': self.bid_volume_total,
            'ask_total': self.ask_volume_total,
            'spread': min(self.asks.keys()) - max(self.bids.keys()) if self.bids and self.asks else 0,
            'imbalance': self.order_flow_imbalance
        }

    def get_order_flow_metrics(self) -> Dict:
        """Get current order flow metrics"""
        if not self.order_flow_history:
            return {}

        recent = self.order_flow_history[-1]
        return {
            'current_imbalance': self.order_flow_imbalance,
            'bid_volume': recent['bid_total'],
            'ask_volume': recent['ask_total'],
            'timestamp': recent['timestamp'],
            'persistence_validated': self.validate_persistence(),
            'imbalance_detected': self.detect_imbalance()
        }