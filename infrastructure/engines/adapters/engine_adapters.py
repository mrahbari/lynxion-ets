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


class BaseEngineAdapter(EnginePort):
    """Base class for engine adapters implementing the EnginePort interface"""
    
    def __init__(self, name: str):
        self.name = name
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal and return enhanced signal"""
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