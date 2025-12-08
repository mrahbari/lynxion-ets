import asyncio
import websockets
import json
from typing import Dict, Callable, Optional
from shared.logger import logger
from shared.event_bus import event_bus
import threading


class WebSocketRouter:
    def __init__(self, base_url: str = "wss://stream.binance.com:9443/ws"):
        self.base_url = base_url
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        
    def register_handler(self, stream_type: str, handler: Callable):
        """Register a handler for a specific stream type"""
        self.handlers[stream_type] = handler
        
    def add_stream(self, stream_name: str, callback: Optional[Callable] = None):
        """Add a stream to listen to"""
        if callback:
            self.handlers[stream_name] = callback
            
    async def start_stream(self, stream_endpoint: str):
        """Start a specific stream"""
        uri = f"{self.base_url}/{stream_endpoint}"
        
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"Connected to stream: {uri}")
                
                while self.running:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Process the message based on its type
                        if 'stream' in data:
                            stream_type = data['stream']
                            if stream_type in self.handlers:
                                self.handlers[stream_type](data)
                        elif 'e' in data:  # Event type for individual streams
                            event_type = data['e']
                            if event_type in self.handlers:
                                self.handlers[event_type](data)
                        else:
                            # Default handler
                            if 'default' in self.handlers:
                                self.handlers['default'](data)
                                
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning(f"Stream {uri} closed, reconnecting...")
                        break
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON: {message}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing message from {uri}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error connecting to stream {uri}: {e}")
            
    def start_all_streams(self, streams: list):
        """Start multiple streams simultaneously"""
        self.running = True
        
        async def run_streams():
            tasks = []
            for stream in streams:
                task = asyncio.create_task(self.start_stream(stream))
                tasks.append(task)
                
            await asyncio.gather(*tasks, return_exceptions=True)
            
        def run_loop():
            asyncio.run(run_streams())
            
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop all streams"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)
            
    def subscribe_to_kline(self, symbol: str, interval: str, callback: Callable):
        """Subscribe to kline/candlestick streams"""
        stream_name = f"{symbol.lower()}@kline_{interval}"
        self.handlers[stream_name] = callback
        
    def subscribe_to_ticker(self, symbol: str, callback: Callable):
        """Subscribe to 24hr ticker streams"""
        stream_name = f"{symbol.lower()}@ticker"
        self.handlers[stream_name] = callback
        
    def subscribe_to_trade(self, symbol: str, callback: Callable):
        """Subscribe to trade streams"""
        stream_name = f"{symbol.lower()}@trade"
        self.handlers[stream_name] = callback
        
    def subscribe_to_orderbook(self, symbol: str, callback: Callable, level: str = "depthUpdate"):
        """Subscribe to orderbook streams"""
        if level == "depthUpdate":
            stream_name = f"{symbol.lower()}@depth"
        elif level == "diffBookDepth":
            stream_name = f"{symbol.lower()}@depth@100ms"
        else:
            stream_name = f"{symbol.lower()}@depth"
            
        self.handlers[stream_name] = callback