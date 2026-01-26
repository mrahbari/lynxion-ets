from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
from decimal import Decimal
from application.configs.configs import Configs


class OrderFlowWSWatcher(BaseWatcher):
    """Order Flow Watcher - analyzes order flow data from WebSocket streams, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 100):
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker

        # Configuration from environment with defaults
        self.enabled = Configs.watcher.orderflow_ws_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'orderflow_ws_watcher_enabled') else True

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

        self.lookback = lookback
        self.order_book_bids = []  # [(price, volume, timestamp), ...]
        self.order_book_asks = []  # [(price, volume, timestamp), ...]
        self.trade_history = []  # [(price, volume, side, timestamp), ...]
        self.aggressive_buy_volume = 0
        self.aggressive_sell_volume = 0
        self.tick_history = []  # [(price, volume, direction), ...]

        # Order flow metrics
        self.bid_volume_history = []
        self.ask_volume_history = []
        self.order_flow_imbalance_history = []

        # Thresholds for different market conditions
        self.high_imbalance_threshold = 0.3
        self.low_imbalance_threshold = -0.3

    def update_data(self, data: dict):
        """Update with new order flow data"""
        if not self.enabled:
            return

        # Update order book if available
        if 'bids' in data and 'asks' in data:
            current_time = datetime.now()
            self.order_book_bids = [(float(price), float(vol), current_time) for price, vol in data['bids']]
            self.order_book_asks = [(float(price), float(vol), current_time) for price, vol in data['asks']]

        # Update trade history if available
        if 'trades' in data:
            for trade in data['trades']:
                self.trade_history.append({
                    'price': float(trade.get('price', 0)),
                    'volume': float(trade.get('amount', trade.get('quantity', 0))),
                    'side': trade.get('side', 'buy').lower(),
                    'timestamp': datetime.now()
                })

            # Keep trade history within limits
            if len(self.trade_history) > self.lookback * 3:
                self.trade_history = self.trade_history[-self.lookback * 3:]

        # Calculate order flow metrics
        self._calculate_order_flow_metrics()

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze order flow and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if not self.order_flow_imbalance_history:
            return None

        # Calculate order flow metrics
        current_imbalance = self.order_flow_imbalance_history[-1] if self.order_flow_imbalance_history else 0
        avg_imbalance = np.mean(self.order_flow_imbalance_history) if self.order_flow_imbalance_history else 0
        imbalance_trend = self._calculate_imbalance_trend()

        # Determine observation type based on order flow conditions
        # Calculate confidence based on the strength of the signal
        imbalance_magnitude = abs(current_imbalance)

        if abs(current_imbalance) < 0.1:  # Low imbalance
            observation_type = 'order_flow_neutral'
            observation_value = 0.0
            # For neutral state, confidence is based on how close to neutral we are
            confidence = min(0.6, (1.0 - imbalance_magnitude))
        elif current_imbalance > self.high_imbalance_threshold:
            observation_type = 'order_flow_buy_pressure'  # Significant buy pressure
            observation_value = abs(current_imbalance)
            confidence = min(0.95, max(0.3, imbalance_magnitude))
        elif current_imbalance < self.low_imbalance_threshold:
            observation_type = 'order_flow_sell_pressure'  # Significant sell pressure
            observation_value = -abs(current_imbalance)
            confidence = min(0.95, max(0.3, imbalance_magnitude))
        else:
            # Moderate imbalance
            if current_imbalance > 0:
                observation_type = 'order_flow_moderate_buy'
                observation_value = abs(current_imbalance)
            else:
                observation_type = 'order_flow_moderate_sell'
                observation_value = -abs(current_imbalance)
            confidence = min(0.85, max(0.3, imbalance_magnitude))

        # Adjust confidence based on trend and consistency
        if abs(imbalance_trend) > 0.1:  # Strong trend in imbalance
            confidence = min(0.9, confidence + 0.2)
        if abs(current_imbalance - avg_imbalance) > 0.1:  # Significantly different from average
            confidence = min(0.9, confidence + 0.1)

        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        # Create and return a MarketObservation instead of a Signal
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=observation_value,
            confidence=confidence_percentage,
            timestamp=datetime.now(),
            metadata={
                'current_order_flow_imbalance': current_imbalance,
                'average_order_flow_imbalance': avg_imbalance,
                'imbalance_trend': imbalance_trend,
                'aggressive_buy_volume': self.aggressive_buy_volume,
                'aggressive_sell_volume': self.aggressive_sell_volume,
                'total_bid_volume': sum(vol for _, vol, _ in self.order_book_bids) if self.order_book_bids else 0,
                'total_ask_volume': sum(vol for _, vol, _ in self.order_book_asks) if self.order_book_asks else 0,
                'order_flow_regime': self._get_order_flow_regime(current_imbalance),
                'order_flow_history_length': len(self.order_flow_imbalance_history),
                'latest_order_flow_timestamp': datetime.now().isoformat(),
                'order_flow_source': self.name,
                'lookback_period': self.lookback
            }
        )

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def _calculate_order_flow_metrics(self):
        """Calculate order flow metrics from trade and order book data"""
        if not self.trade_history:
            return

        # Calculate aggressive buy/sell volumes
        recent_trades = self.trade_history[-self.lookback:] if len(self.trade_history) > self.lookback else self.trade_history

        buy_volume = sum(trade['volume'] for trade in recent_trades if trade['side'] == 'buy')
        sell_volume = sum(trade['volume'] for trade in recent_trades if trade['side'] == 'sell')

        self.aggressive_buy_volume = buy_volume
        self.aggressive_sell_volume = sell_volume

        # Calculate order flow imbalance
        total_volume = buy_volume + sell_volume
        if total_volume > 0:
            imbalance = (buy_volume - sell_volume) / total_volume
        else:
            imbalance = 0

        self.order_flow_imbalance_history.append(imbalance)

        # Keep history within limits
        if len(self.order_flow_imbalance_history) > self.lookback * 3:
            self.order_flow_imbalance_history.pop(0)

    def _calculate_imbalance_trend(self) -> float:
        """Calculate the trend in order flow imbalance"""
        if len(self.order_flow_imbalance_history) < 3:
            return 0.0

        recent_imbalances = self.order_flow_imbalance_history[-10:] if len(self.order_flow_imbalance_history) >= 10 else self.order_flow_imbalance_history
        x = np.arange(len(recent_imbalances))

        if len(x) > 1:
            slope = (len(x) * np.sum(x * recent_imbalances) - np.sum(x) * np.sum(recent_imbalances)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

            # Normalize by average imbalance
            avg_imbalance = np.mean(recent_imbalances)
            if avg_imbalance != 0:
                return slope / avg_imbalance
            else:
                return slope

        return 0.0

    def _get_order_flow_regime(self, imbalance: float) -> str:
        """Get current order flow regime"""
        if abs(imbalance) > self.high_imbalance_threshold:
            return "extreme"
        elif imbalance > 0.1:
            return "buy_pressure"
        elif imbalance < -0.1:
            return "sell_pressure"
        else:
            return "neutral"