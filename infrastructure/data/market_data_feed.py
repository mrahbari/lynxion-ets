"""
Market data feed service for the enterprise hedge fund trading system.
Provides real-time market data to watchers, engines, and strategies.
"""
import asyncio
import websockets
import json
import threading
import weakref
from typing import Dict, List, Callable, Any
from datetime import datetime
import time
import requests
from decimal import Decimal

from domain.entities import OrderSide
from domain.value_objects import Symbol, Money
from shared.logger import logger


class MarketDataFeed:
    """Service to provide market data to the system, acting as a thread-safe passive cache."""
    
    _active_instances = weakref.WeakSet()
    
    def __init__(self):
        self.symbols = set()
        self.data_handlers = {}  # symbol -> [handlers]
        self.price_cache = {}  # symbol -> {price: float, timestamp: datetime}
        self.running = False
        self._lock = threading.Lock()
        MarketDataFeed._active_instances.add(self)
        
    def add_symbol(self, symbol: Symbol):
        """Add a symbol to the data feed"""
        with self._lock:
            self.symbols.add(symbol.value)
            if symbol.value not in self.data_handlers:
                self.data_handlers[symbol.value] = []
            if symbol.value not in self.price_cache:
                self.price_cache[symbol.value] = {'price': 0.0, 'timestamp': datetime.now()}
    
    def remove_symbol(self, symbol: Symbol):
        """Remove a symbol from the data feed"""
        with self._lock:
            symbol_str = symbol.value
            if symbol_str in self.symbols:
                self.symbols.remove(symbol_str)
                if symbol_str in self.data_handlers:
                    del self.data_handlers[symbol_str]
                if symbol_str in self.price_cache:
                    del self.price_cache[symbol_str]
    
    def register_handler(self, symbol: Symbol, handler: Callable[[Dict[str, Any]], None]):
        """Register a handler for market data updates for a symbol"""
        with self._lock:
            symbol_str = symbol.value
            if symbol_str not in self.data_handlers:
                self.data_handlers[symbol_str] = []
            self.data_handlers[symbol_str].append(handler)
    
    def start_feed(self):
        """Start the market data feed (passive cache activation)"""
        self.running = True
        logger.info(f"Starting passive market data feed cache for symbols: {list(self.symbols)}")
    
    def stop_feed(self):
        """Stop the market data feed"""
        self.running = False
        logger.info("Stopping passive market data feed cache")
        
    def on_trade_tick(self, trade_tick: Any) -> None:
        """Callback receiver to update cache and notify handlers on new trade ticks"""
        if not self.running:
            return
            
        symbol = trade_tick.symbol
        price = float(trade_tick.price.value)
        timestamp_ms = int(trade_tick.timestamp.millis)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)
        
        price_data = {
            'symbol': symbol.value,
            'price': price,
            'time': timestamp_ms / 1000.0,
            'volume': float(trade_tick.quantity.value),
            'high': price,
            'low': price,
            'open': price
        }
        
        with self._lock:
            if symbol.value in self.symbols:
                self.price_cache[symbol.value] = {
                    'price': price,
                    'timestamp': timestamp
                }
                
        self._notify_handlers(symbol.value, price_data)
        
    def _notify_handlers(self, symbol_str: str, data: Dict[str, Any]):
        """Notify all registered handlers about new data"""
        with self._lock:
            handlers = list(self.data_handlers.get(symbol_str, []))
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error notifying handler for {symbol_str}: {e}")
    
    def get_current_price(self, symbol: Symbol) -> float:
        """Get the current cached price for a symbol"""
        with self._lock:
            cached = self.price_cache.get(symbol.value)
            if cached:
                return cached['price']
            return 0.0
    
    def get_cached_data(self, symbol: Symbol) -> Dict[str, Any]:
        """Get the most recent cached data for a symbol"""
        with self._lock:
            cached = self.price_cache.get(symbol.value)
            if cached:
                return {
                    'symbol': symbol.value,
                    'close': cached['price'],
                    'timestamp': cached['timestamp'],
                    'volume': 100  # Placeholder/legacy compatibility
                }
            return {}


class BacktestingMarketDataFeed:
    """Market data feed for backtesting purposes"""
    
    def __init__(self, historical_data: Dict[Symbol, List[Dict[str, Any]]]):
        self.historical_data = historical_data
        self.positions = {symbol: 0 for symbol in historical_data.keys()}
        self.data_handlers = {}
    
    def add_symbol(self, symbol: Symbol):
        """Add symbol to backtesting feed"""
        if symbol not in self.data_handlers:
            self.data_handlers[symbol] = []
    
    def register_handler(self, symbol: Symbol, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for backtesting data"""
        if symbol not in self.data_handlers:
            self.data_handlers[symbol] = []
        self.data_handlers[symbol].append(handler)
    
    def start_feed(self):
        """Start backtesting feed"""
        for symbol, data_list in self.historical_data.items():
            for data in data_list:
                # Simulate real-time data delivery
                self._notify_handlers(symbol, data)
                time.sleep(0.01)  # Small delay to simulate real-time
    
    def _notify_handlers(self, symbol: Symbol, data: Dict[str, Any]):
        """Notify handlers in backtesting mode"""
        handlers = self.data_handlers.get(symbol, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in backtesting handler: {e}")
    
    def stop_feed(self):
        """Stop backtesting feed"""
        pass  # Nothing to stop in backtesting mode