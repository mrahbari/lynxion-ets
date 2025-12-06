from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np
from typing import Dict, List, Optional
import threading
import queue


class OrderFlowWSWatcher(BaseWatcher):
    """Order Flow Watcher using WebSocket - analyzes order book dynamics"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, depth_levels: int = 10):
        super().__init__(name, symbol, broker_service, target_broker)
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

        # Signal thresholds
        self.imbalance_threshold = 0.1
        self.volume_spike_threshold = 2.0  # 2x average volume

        # WebSocket connection (simulated)
        self.ws_connected = False
        self.data_queue = queue.Queue()
        
    def update_data(self, data: Dict):
        """Update with new market data (order book updates)"""
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
        """Calculate order flow metrics"""
        if self.bid_volume_total + self.ask_volume_total == 0:
            self.order_flow_imbalance = 0
            return
            
        # Calculate order flow imbalance (bids vs asks)
        self.order_flow_imbalance = (self.bid_volume_total - self.ask_volume_total) / (self.bid_volume_total + self.ask_volume_total)
        
        # Add to history
        self.order_flow_history.append({
            'timestamp': datetime.now(),
            'imbalance': self.order_flow_imbalance,
            'bid_total': self.bid_volume_total,
            'ask_total': self.ask_volume_total
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
        if not self.order_flow_history or len(self.order_flow_history) < 5:
            return None

        # Get recent order flow data
        recent_data = self.order_flow_history[-5:]

        # Calculate average recent imbalance
        avg_imbalance = np.mean([d['imbalance'] for d in recent_data])

        # Calculate volume metrics
        recent_bid_avg = np.mean([d['bid_total'] for d in recent_data])
        recent_ask_avg = np.mean([d['ask_total'] for d in recent_data])

        # Determine signal based on order flow metrics
        if avg_imbalance > self.imbalance_threshold:
            # Significant bid imbalance - potential bullish signal
            signal_type = SignalType.BUY
            confidence = min(1.0, abs(avg_imbalance) / self.imbalance_threshold)
        elif avg_imbalance < -self.imbalance_threshold:
            # Significant ask imbalance - potential bearish signal
            signal_type = SignalType.SELL
            confidence = min(1.0, abs(avg_imbalance) / self.imbalance_threshold)
        else:
            # Balanced market - hold
            signal_type = SignalType.HOLD
            confidence = 0.6  # Medium confidence in hold during balanced conditions

        # Adjust confidence based on volume confirmation
        volume_confirmation = self.check_volume_confirmation()
        if volume_confirmation > 0:
            # Positive volume confirmation increases confidence
            confidence = min(1.0, confidence + 0.2)
        elif volume_confirmation < 0:
            # Negative volume confirmation decreases confidence
            confidence = max(0.1, confidence - 0.2)

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=avg_imbalance,
            strategy=self.name,
            timestamp=datetime.now()
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"OrderFlowWSWatcher {self.name} generated signal: {signal_type} with imbalance {avg_imbalance:.3f}")

        return signal
        
    def check_volume_confirmation(self) -> int:
        """Check if volume confirms the directional bias"""
        if not self.order_flow_history or len(self.order_flow_history) < 10:
            return 0
            
        # Compare recent volumes to historical average
        recent_data = self.order_flow_history[-5:]
        
        # Calculate historical average (excluding recent)
        historical_data = self.order_flow_history[:-5] if len(self.order_flow_history) > 5 else self.order_flow_history
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
        imbalance = self.order_flow_history[-1]['imbalance'] if self.order_flow_history else 0
        
        if imbalance > 0 and bid_volume_spike > self.volume_spike_threshold:
            return 1  # Bullish confirmation
        elif imbalance < 0 and ask_volume_spike > self.volume_spike_threshold:
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
            'timestamp': recent['timestamp']
        }