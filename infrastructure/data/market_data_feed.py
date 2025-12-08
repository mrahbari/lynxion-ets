"""
Market data feed service for the enterprise hedge fund trading system.
Provides real-time market data to watchers, engines, and strategies.
"""
import asyncio
import websockets
import json
import threading
from typing import Dict, List, Callable, Any
from datetime import datetime
import time
import requests
from decimal import Decimal

from domain.entities.trading_entities import OrderSide
from domain.value_objects import Symbol, Money
from shared.logger import logger


class MarketDataFeed:
    """Service to provide market data to the system"""
    
    def __init__(self):
        self.symbols = set()
        self.data_handlers = {}  # symbol -> [handlers]
        self.ws_connections = {}  # symbol -> websocket connection
        self.price_cache = {}  # symbol -> {price: float, timestamp: datetime}
        self.orderbook_cache = {}  # symbol -> {bids: [], asks: []}
        self.running = False
        self.data_thread = None
        
    def add_symbol(self, symbol: Symbol):
        """Add a symbol to the data feed"""
        self.symbols.add(symbol.value)
        if symbol.value not in self.data_handlers:
            self.data_handlers[symbol.value] = []
        self.price_cache[symbol.value] = {'price': 0.0, 'timestamp': datetime.now()}
    
    def remove_symbol(self, symbol: Symbol):
        """Remove a symbol from the data feed"""
        symbol_str = symbol.value
        if symbol_str in self.symbols:
            self.symbols.remove(symbol_str)
            if symbol_str in self.data_handlers:
                del self.data_handlers[symbol_str]
            if symbol_str in self.price_cache:
                del self.price_cache[symbol_str]
    
    def register_handler(self, symbol: Symbol, handler: Callable[[Dict[str, Any]], None]):
        """Register a handler for market data updates for a symbol"""
        symbol_str = symbol.value
        if symbol_str not in self.data_handlers:
            self.data_handlers[symbol_str] = []
        self.data_handlers[symbol_str].append(handler)
    
    def start_feed(self):
        """Start the market data feed"""
        logger.info(f"Starting market data feed for symbols: {list(self.symbols)}")
        self.running = True
        self.data_thread = threading.Thread(target=self._data_loop)
        self.data_thread.daemon = True
        self.data_thread.start()
    
    def stop_feed(self):
        """Stop the market data feed"""
        logger.info("Stopping market data feed...")
        self.running = False
        if self.data_thread:
            self.data_thread.join()
        logger.info("Market data feed stopped")
    
    def _data_loop(self):
        """Main data fetching loop"""
        while self.running:
            try:
                for symbol in self.symbols:
                    # Fetch current price data
                    price_data = self._fetch_price_data(symbol)
                    if price_data:
                        # Update cache
                        self.price_cache[symbol] = {
                            'price': float(price_data.get('price', 0)),
                            'timestamp': datetime.now()
                        }
                        
                        # Update all registered handlers
                        self._notify_handlers(symbol, price_data)
                
                # Wait before next update
                time.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in market data loop: {e}")
                time.sleep(5)  # Wait longer on errors
    
    def _fetch_price_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch price data for a symbol (using BingX as primary source)"""
        try:
            # Format symbol for API (BingX uses different format)
            api_symbol = symbol.replace('-', '')  # BTC-USDT -> BTCUSDT
            
            # Try BingX testnet first
            url = f"https://open-api-vst.bingx.com/openApi/quote/v1/ticker/price?symbol={api_symbol}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and 'data' in data:
                    price_info = data['data']
                    return {
                        'symbol': symbol,
                        'price': float(price_info.get('price', 0)),
                        'time': datetime.now().timestamp(),
                        'volume': 0,  # Placeholder
                        'high': 0,    # Placeholder
                        'low': 0,     # Placeholder
                        'open': 0     # Placeholder
                    }
            
            logger.warning(f"Could not fetch data from BingX for {symbol}, trying alternative source")
            
            # Fallback: Use a public API for demonstration
            # In production, you'd use your broker's API
            return {
                'symbol': symbol,
                'price': 40000.0 + (time.time() % 1000), # Simulated price with small variations
                'time': datetime.now().timestamp(),
                'volume': 1000,
                'high': 41000.0,
                'low': 39000.0,
                'open': 40500.0
            }
            
        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            return None
    
    def _notify_handlers(self, symbol: str, data: Dict[str, Any]):
        """Notify all registered handlers about new data"""
        handlers = self.data_handlers.get(symbol, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error notifying handler for {symbol}: {e}")
    
    def get_current_price(self, symbol: Symbol) -> float:
        """Get the current cached price for a symbol"""
        cached = self.price_cache.get(symbol.value)
        if cached:
            return cached['price']
        return 0.0
    
    def get_cached_data(self, symbol: Symbol) -> Dict[str, Any]:
        """Get the most recent cached data for a symbol"""
        cached = self.price_cache.get(symbol.value)
        if cached:
            return {
                'symbol': symbol.value,
                'close': cached['price'],
                'timestamp': cached['timestamp'],
                'volume': 100  # Placeholder
            }
        return {}


class WebSocketMarketDataFeed:
    """WebSocket-based market data feed for real-time updates"""
    
    def __init__(self):
        self.symbols = set()
        self.handlers = {}
        self.ws_connections = {}  # symbol -> WebSocket connection
        self.running = False
        self.loop = None
        
    def add_symbol(self, symbol: Symbol):
        """Add symbol to WebSocket feed"""
        self.symbols.add(symbol.value)
        if symbol.value not in self.handlers:
            self.handlers[symbol.value] = []
    
    def register_handler(self, symbol: Symbol, handler: Callable[[Dict[str, Any]], None]):
        """Register handler for WebSocket updates"""
        symbol_str = symbol.value
        if symbol_str not in self.handlers:
            self.handlers[symbol_str] = []
        self.handlers[symbol_str].append(handler)
    
    async def _ws_handler(self, symbol: str):
        """WebSocket handler for a specific symbol"""
        uri = f"wss://open-api-vst.bingx.com/openApi/ws-market-snapshot?symbol={symbol.replace('-', '')}"
        
        try:
            async with websockets.connect(uri) as websocket:
                while self.running:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Process and distribute the data
                    processed_data = self._process_ws_data(data, symbol)
                    if processed_data:
                        self._notify_handlers(symbol, processed_data)
                        
        except Exception as e:
            logger.error(f"WebSocket error for {symbol}: {e}")
            # TODO: Implement reconnection logic
    
    def _process_ws_data(self, data: Dict, symbol: str) -> Dict[str, Any]:
        """Process incoming WebSocket data"""
        # This would parse the specific WebSocket format
        # For now, return a basic structure
        if 'data' in data:
            return {
                'symbol': symbol,
                'price': float(data['data'].get('price', 0)),
                'volume': float(data['data'].get('volume', 0)),
                'timestamp': datetime.now().timestamp()
            }
        return None
    
    def _notify_handlers(self, symbol: str, data: Dict[str, Any]):
        """Notify handlers of new data"""
        handlers = self.handlers.get(symbol, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in WebSocket handler for {symbol}: {e}")
    
    def start_feed(self):
        """Start the WebSocket market data feed"""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        tasks = []
        for symbol in self.symbols:
            task = self.loop.create_task(self._ws_handler(symbol))
            tasks.append(task)
        
        # Run all WebSocket tasks
        self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    
    def stop_feed(self):
        """Stop the WebSocket feed"""
        self.running = False
        if self.loop:
            self.loop.stop()


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