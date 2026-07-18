import logging
import math
from decimal import Decimal
from typing import Dict, Any, List, Optional

from domain.ports.data_ports import FeatureGeneratorPort
from domain.value_objects import Symbol, ExchangeTimestamp, Side
from domain.entities import (
    TradeTick,
    OrderBookSnapshot,
    FeatureSnapshot,
)
from domain.entities.order_book import OrderBookBuilder

logger = logging.getLogger("Lynxion.FeatureGenerator")


class NGLSFeatureGenerator(FeatureGeneratorPort):
    """Concrete generator for calculating Next Generation Liquidity Sweep (NGLS) alpha features."""

    def __init__(self, symbol: Symbol, regime_volatility_threshold: Decimal = Decimal("15.0")):
        self.symbol = symbol
        self.regime_volatility_threshold = regime_volatility_threshold
        
        # Underlying reconstruction engine
        self.order_book_builder = OrderBookBuilder(symbol)

        # Trade buffers
        self.trade_ticks: List[TradeTick] = []
        self.max_trade_buffer = 100

        # CVD trackers
        self.cumulative_delta = Decimal("0")

        # OBI state trackers (for velocity calculations)
        self.previous_obi_ratio = Decimal("0")
        self.last_obi_timestamp: Optional[ExchangeTimestamp] = None

        # Sweep state trackers
        self.recent_high = Decimal("0")
        self.recent_low = Decimal("999999999")

    def generate_features(self, symbol: Symbol, start: Any, end: Any) -> Dict[str, Any]:
        """Historical window feature generation interface (no-op for online simulation)."""
        return {}

    def update_feature_online(self, symbol: Symbol, new_data: Any) -> Dict[str, Any]:
        """Incremental update interface. Processes order book snapshots or trade ticks."""
        if isinstance(new_data, OrderBookSnapshot):
            self.order_book_builder.apply_snapshot(new_data)
        elif isinstance(new_data, TradeTick):
            self.process_trade(new_data)
        
        return self.get_feature_snapshot().to_dict()

    def process_trade(self, tick: TradeTick):
        """Append trade, update CVD, and adjust recent swing high/low bands."""
        if tick.symbol != self.symbol:
            return

        self.trade_ticks.append(tick)
        if len(self.trade_ticks) > self.max_trade_buffer:
            self.trade_ticks.pop(0)

        # Update Cumulative Volume Delta (CVD)
        if tick.side == Side.BUY:
            self.cumulative_delta += tick.quantity.value
        else:
            self.cumulative_delta -= tick.quantity.value

        # Update swing boundaries over last 20 trades
        recent_prices = [t.price.value for t in self.trade_ticks[-20:]]
        if recent_prices:
            self.recent_high = max(recent_prices)
            self.recent_low = min(recent_prices)

    def get_feature_snapshot(self) -> FeatureSnapshot:
        """Calculate and return a normalized FeatureSnapshot based on current state."""
        best_bid = self.order_book_builder.state.get_best_bid()
        best_ask = self.order_book_builder.state.get_best_ask()
        
        # 1. Order Book Imbalance (OBI)
        obi_ratio = Decimal("0")
        if best_bid is not None and best_ask is not None:
            bid_qty = self.order_book_builder.state.bids.get(best_bid, Decimal("0"))
            ask_qty = self.order_book_builder.state.asks.get(best_ask, Decimal("0"))
            if bid_qty + ask_qty > 0:
                obi_ratio = (bid_qty - ask_qty) / (bid_qty + ask_qty)

        # Multi-level imbalance (top 5 levels)
        bids_5, asks_5 = self.order_book_builder.state.get_depth(5)
        total_bid_5 = sum(level[1] for level in bids_5)
        total_ask_5 = sum(level[1] for level in asks_5)
        obi_multi_level = Decimal("0")
        if total_bid_5 + total_ask_5 > 0:
            obi_multi_level = (total_bid_5 - total_ask_5) / (total_bid_5 + total_ask_5)

        # OBI velocity
        obi_velocity = Decimal("0")
        current_ts = self.order_book_builder.state.timestamp
        if self.last_obi_timestamp and current_ts:
            dt_ms = current_ts.to_millis() - self.last_obi_timestamp.to_millis()
            if dt_ms > 0:
                dt_sec = Decimal(str(dt_ms)) / Decimal("1000.0")
                obi_velocity = (obi_ratio - self.previous_obi_ratio) / dt_sec

        self.previous_obi_ratio = obi_ratio
        self.last_obi_timestamp = current_ts

        # 2. Trade Flow Delta (CVD)
        # Sum last 20 trade buy vs sell volumes
        buy_volume = Decimal("0")
        sell_volume = Decimal("0")
        recent_trades = self.trade_ticks[-20:]
        for t in recent_trades:
            if t.side == Side.BUY:
                buy_volume += t.quantity.value
            else:
                sell_volume += t.quantity.value
        delta = buy_volume - sell_volume

        # 3. Liquidity Sweep Detection
        # A sweep is triggered if the latest trade penetrated the recent 20-trade high/low,
        # but the current mid-price returns back inside the previous 10-trade average range.
        is_sweep = False
        sweep_level_price = None
        sweep_volume_consumed = Decimal("0")
        sweep_rejection_ratio = Decimal("0")

        if len(self.trade_ticks) >= 10:
            latest_trade = self.trade_ticks[-1]
            last_price = latest_trade.price.value
            
            # Check if last price penetrated swing high/low
            # (using historical high/low excluding the latest tick)
            prev_high = max(t.price.value for t in self.trade_ticks[:-1]) if len(self.trade_ticks) > 1 else last_price
            prev_low = min(t.price.value for t in self.trade_ticks[:-1]) if len(self.trade_ticks) > 1 else last_price
            
            mid_price = self.order_book_builder.state.get_mid_price()
            if mid_price is not None:
                # Reverted back inside
                if last_price >= prev_high and mid_price < prev_high:
                    is_sweep = True
                    sweep_level_price = last_price
                    sweep_volume_consumed = latest_trade.quantity.value
                    penetration = last_price - prev_high
                    pullback = prev_high - mid_price
                    sweep_rejection_ratio = pullback / penetration if penetration > 0 else Decimal("1")
                elif last_price <= prev_low and mid_price > prev_low:
                    is_sweep = True
                    sweep_level_price = last_price
                    sweep_volume_consumed = latest_trade.quantity.value
                    penetration = prev_low - last_price
                    pullback = mid_price - prev_low
                    sweep_rejection_ratio = pullback / penetration if penetration > 0 else Decimal("1")

        # 4. Absorption Detection
        # Triggers if rolling trade volume is extremely high but price moves very little
        is_absorption = False
        absorption_volume = Decimal("0")
        absorption_price_range = Decimal("0")
        
        if len(self.trade_ticks) >= 10:
            last_10 = self.trade_ticks[-10:]
            absorption_volume = sum(t.quantity.value for t in last_10)
            prices_10 = [t.price.value for t in last_10]
            absorption_price_range = max(prices_10) - min(prices_10)
            
            # High volume (relative) and tight range
            if absorption_volume > Decimal("10.0") and absorption_price_range < Decimal("5.0"):
                is_absorption = True

        # 5. Market Context
        volatility = self._calculate_volatility()
        spread = Decimal("0")
        if best_bid is not None and best_ask is not None:
            spread = best_ask - best_bid

        # Total depth top 10
        bids_10, asks_10 = self.order_book_builder.state.get_depth(10)
        depth_total = sum(level[1] for level in bids_10) + sum(level[1] for level in asks_10)

        # Regime context
        if volatility > self.regime_volatility_threshold:
            regime_context = "HIGH_VOLATILITY"
        else:
            # Check price trend direction
            if len(self.trade_ticks) >= 10:
                first_avg = sum(t.price.value for t in self.trade_ticks[:5]) / 5
                last_avg = sum(t.price.value for t in self.trade_ticks[-5:]) / 5
                if abs(last_avg - first_avg) > Decimal("10.0"):
                    regime_context = "TRENDING"
                else:
                    regime_context = "RANGING"
            else:
                regime_context = "RANGING"

        # Determine appropriate timestamp
        if current_ts:
            latest_ts = current_ts
        elif self.trade_ticks:
            latest_ts = self.trade_ticks[-1].timestamp
        else:
            latest_ts = ExchangeTimestamp(1)

        return FeatureSnapshot(
            symbol=self.symbol,
            timestamp=latest_ts,
            obi_ratio=obi_ratio,
            obi_multi_level=obi_multi_level,
            obi_velocity=obi_velocity,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            delta=delta,
            cumulative_delta=self.cumulative_delta,
            is_sweep=is_sweep,
            sweep_level_price=sweep_level_price,
            sweep_volume_consumed=sweep_volume_consumed,
            sweep_rejection_ratio=sweep_rejection_ratio,
            is_absorption=is_absorption,
            absorption_volume=absorption_volume,
            absorption_price_range=absorption_price_range,
            volatility=volatility,
            spread=spread,
            depth_total=depth_total,
            regime_context=regime_context
        )

    def _calculate_volatility(self) -> Decimal:
        """Calculate the standard deviation of recent trade prices using high-precision Decimal."""
        recent_prices = [t.price.value for t in self.trade_ticks[-20:]]
        n = len(recent_prices)
        if n < 2:
            return Decimal("0")
        
        mean = sum(recent_prices) / Decimal(n)
        variance = sum((p - mean) ** 2 for p in recent_prices) / Decimal(n - 1)
        
        # Decimal square root
        return variance.sqrt()
