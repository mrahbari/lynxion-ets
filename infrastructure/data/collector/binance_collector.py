import asyncio
import json
import time
import httpx
import websockets
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from datetime import datetime, timezone
from decimal import Decimal

from domain.ports.data_ports import MarketDataCollectorPort
from domain.value_objects import Symbol, ExchangeTimestamp, Price, Quantity, Side
from domain.entities import (
    TradeTick,
    OrderBookLevel,
    OrderBookSnapshot,
    MarkPrice,
    FundingRate,
    OpenInterest,
    LiquidationEvent,
)

logger = logging.getLogger("Lynxion.MarketDataCollector")


class BinanceMarketDataCollector(MarketDataCollectorPort):
    """Production-grade market data collector for Binance Futures."""

    def __init__(self,
                 ws_url: str = "wss://fstream.binance.com/ws",
                 rest_url: str = "https://fapi.binance.com",
                 http_client: Optional[httpx.AsyncClient] = None,
                 ws_client: Optional[Any] = None,
                 reconnect_delay: float = 1.0,
                 max_reconnect_delay: float = 60.0,
                 heartbeat_interval: float = 15.0):
        self.ws_url = ws_url
        self.rest_url = rest_url
        self.http_client = http_client or httpx.AsyncClient()
        self.ws_client_override = ws_client

        # Reconnect parameters
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.current_reconnect_delay = reconnect_delay
        self.heartbeat_interval = heartbeat_interval

        # State management
        self.symbols: List[Symbol] = []
        self.callbacks: Dict[str, Callable[[Any], None]] = {}
        self.active_connections: Dict[str, Any] = {}
        self._running = False
        self._connected = False
        
        # Async tasks
        self._tasks: List[asyncio.Task] = []
        self._oi_task: Optional[asyncio.Task] = None

        # Tracking state for data validation and duplicate filtering
        self.last_trade_ids: Dict[str, Set[int]] = {}  # symbol -> set of recent trade IDs
        self.last_update_ids: Dict[str, int] = {}       # symbol -> last update ID of L2 diff book
        self.book_buffered_updates: Dict[str, List[Dict[str, Any]]] = {} # symbol -> buffered diffs during sync
        self.book_snapshot_syncing: Dict[str, bool] = {} # symbol -> is syncing snapshot
        self.last_heartbeat_time: float = 0.0

        # Health/Quality metrics
        self.metrics = {
            "messages_received": 0,
            "reconnects": 0,
            "gap_detections": 0,
            "duplicate_messages": 0,
            "malformed_messages": 0,
            "heartbeat_failures": 0,
        }

    def start_collecting(self, symbols: List[Symbol], callbacks: Dict[str, Callable[[Any], None]]) -> None:
        """Start real-time data collection for specified symbols and callbacks."""
        self.symbols = symbols
        self.callbacks = callbacks
        self._running = True
        self.last_heartbeat_time = time.time()
        
        # Clean caches
        for symbol in symbols:
            self.last_trade_ids[symbol.value] = set()
            self.last_update_ids[symbol.value] = 0
            self.book_buffered_updates[symbol.value] = []
            self.book_snapshot_syncing[symbol.value] = False

        # Launch websocket runner task
        loop = asyncio.get_event_loop()
        ws_task = loop.create_task(self._websocket_loop())
        self._tasks.append(ws_task)

        # Launch REST Open Interest polling loop
        oi_task = loop.create_task(self._poll_open_interest())
        self._tasks.append(oi_task)
        self._oi_task = oi_task

        logger.info(f"Started collecting market data for {len(symbols)} symbols")

    def stop_collecting(self) -> None:
        """Stop data streams and close connections."""
        self._running = False
        self._connected = False
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        self._tasks.clear()

        # Close HTTP client
        # Note: HTTP client is not closed here if it was injected
        logger.info("Stopped collecting market data collector layer")

    def is_connected(self) -> bool:
        """Return True if connection to WebSocket stream is active."""
        return self._connected

    def get_metrics(self) -> Dict[str, int]:
        """Return collector metrics."""
        return self.metrics

    async def _websocket_loop(self):
        """Primary WebSocket manager loop handling reconnects and backoffs."""
        while self._running:
            try:
                stream_names = []
                for symbol in self.symbols:
                    s_lower = symbol.value.lower().replace("-", "").replace("_", "")
                    stream_names.extend([
                        f"{s_lower}@trade",
                        f"{s_lower}@depth5@100ms", # Partial book depth 5 levels
                        f"{s_lower}@depth@100ms",   # Diff depth updates
                        f"{s_lower}@markPrice@1s",  # Mark price + funding rate
                        f"{s_lower}@forceOrder",    # Liquidation events
                    ])

                # Construct connection URI with stream subscription params
                connect_uri = f"{self.ws_url}/stream?streams={'/'.join(stream_names)}"
                logger.info(f"Connecting to Binance stream URI: {connect_uri}")

                # WebSocket client override for testing or standard connection
                if self.ws_client_override:
                    websocket = self.ws_client_override
                else:
                    websocket = await websockets.connect(connect_uri)

                self._connected = True
                self.current_reconnect_delay = self.reconnect_delay
                logger.info("Successfully connected to Binance Futures WebSocket")

                # Launch heartbeat check monitor in parallel
                heartbeat_task = asyncio.get_event_loop().create_task(self._monitor_heartbeat(websocket))

                try:
                    while self._running:
                        message = await websocket.recv()
                        self.last_heartbeat_time = time.time()
                        self.metrics["messages_received"] += 1
                        
                        try:
                            payload = json.loads(message)
                            if "stream" in payload and "data" in payload:
                                await self._process_stream_data(payload["stream"], payload["data"])
                        except json.JSONDecodeError:
                            self.metrics["malformed_messages"] += 1
                            logger.warning(f"Discarding malformed JSON packet: {message}")
                except Exception as e:
                    logger.warning(f"WebSocket execution exception: {e}")
                finally:
                    heartbeat_task.cancel()
                    self._connected = False
                    await websocket.close()
            except Exception as conn_err:
                logger.error(f"WebSocket connection error: {conn_err}")

            if self._running:
                logger.info(f"Attempting reconnection in {self.current_reconnect_delay:.2f} seconds...")
                self.metrics["reconnects"] += 1
                await asyncio.sleep(self.current_reconnect_delay)
                # Exponential backoff with ceiling
                self.current_reconnect_delay = min(self.current_reconnect_delay * 2, self.max_reconnect_delay)

    async def _monitor_heartbeat(self, websocket):
        """Monitor connection quietness; force reconnection on timeout."""
        while self._running:
            await asyncio.sleep(min(5.0, self.heartbeat_interval))
            if time.time() - self.last_heartbeat_time > self.heartbeat_interval:
                logger.warning("Heartbeat timeout! No WebSocket payload received. Force disconnecting connection.")
                self.metrics["heartbeat_failures"] += 1
                await websocket.close()
                break

    async def _process_stream_data(self, stream_name: str, data: Dict[str, Any]):
        """Normalize, validate, and route incoming stream records."""
        event_type = data.get("e")
        symbol_str = data.get("s")
        if not symbol_str and "@" in stream_name:
            symbol_str = stream_name.split("@")[0].upper()
        if not symbol_str:
            return

        # Find matching domain Symbol object
        matching_symbol = next((s for s in self.symbols if s.value.lower().replace("-", "").replace("_", "") == symbol_str.lower()), None)
        if not matching_symbol:
            return

        # 1. Trade Ticks
        if event_type == "trade":
            trade_id = data.get("t")
            # Duplicate check
            recent_ids = self.last_trade_ids[matching_symbol.value]
            if trade_id in recent_ids:
                self.metrics["duplicate_messages"] += 1
                return
            
            # Keep set size capped
            recent_ids.add(trade_id)
            if len(recent_ids) > 1000:
                recent_ids.pop()

            try:
                # Invariant validations & conversions
                trade_tick = TradeTick(
                    symbol=matching_symbol,
                    trade_id=trade_id,
                    price=Price(Decimal(str(data.get("p"))), matching_symbol),
                    quantity=Quantity(Decimal(str(data.get("q"))), matching_symbol.base_asset()),
                    timestamp=ExchangeTimestamp(int(data.get("T", 0))),
                    side=Side.BUY if not data.get("m") else Side.SELL # m=True means buyer maker -> sell aggressor
                )
                self._dispatch("trade", trade_tick)
            except Exception as val_err:
                self.metrics["malformed_messages"] += 1
                logger.warning(f"Discarding invalid trade tick: {val_err}")

        # 2. Mark Price and Funding Rate
        elif event_type == "markPriceUpdate":
            try:
                ts = ExchangeTimestamp(int(data.get("E", 0)))
                # Mark price
                mark_price = MarkPrice(
                    symbol=matching_symbol,
                    price=Price(Decimal(str(data.get("p"))), matching_symbol),
                    timestamp=ts
                )
                # Funding rate
                funding_rate = FundingRate(
                    symbol=matching_symbol,
                    rate=Decimal(str(data.get("r", 0.0))),
                    timestamp=ts,
                    next_funding_time=ExchangeTimestamp(int(data.get("T", 0)))
                )
                self._dispatch("mark_price", mark_price)
                self._dispatch("funding", funding_rate)
            except Exception as val_err:
                self.metrics["malformed_messages"] += 1
                logger.warning(f"Discarding invalid mark/funding event: {val_err}")

        # 3. Partial Book Depth (Top 5 Bids/Asks)
        elif "depth5" in stream_name:
            try:
                # Normalizes immediately to L2 snapshots
                ts = ExchangeTimestamp(int(data.get("E", 0)))
                bids = [
                    OrderBookLevel(Price(Decimal(str(b[0])), matching_symbol), Quantity(Decimal(str(b[1])), matching_symbol.base_asset()))
                    for b in data.get("b", [])
                ]
                asks = [
                    OrderBookLevel(Price(Decimal(str(a[0])), matching_symbol), Quantity(Decimal(str(a[1])), matching_symbol.base_asset()))
                    for a in data.get("a", [])
                ]
                snapshot = OrderBookSnapshot(
                    symbol=matching_symbol,
                    timestamp=ts,
                    bids=bids,
                    asks=asks,
                    sequence_id=int(data.get("lastUpdateId", 0))
                )
                self._dispatch("depth_partial", snapshot)
            except Exception as val_err:
                self.metrics["malformed_messages"] += 1
                logger.warning(f"Discarding invalid partial depth update: {val_err}")

        # 4. Diff Book Depth Updates (Contiguity and REST Sync)
        elif event_type == "depthUpdate":
            await self._process_diff_depth(matching_symbol, data)

        # 5. Liquidation Streams
        elif event_type == "forceOrder":
            try:
                order_details = data.get("o", {})
                liq_event = LiquidationEvent(
                    symbol=matching_symbol,
                    side=Side.BUY if order_details.get("S") == "BUY" else Side.SELL,
                    price=Price(Decimal(str(order_details.get("p"))), matching_symbol),
                    quantity=Quantity(Decimal(str(order_details.get("q"))), matching_symbol.base_asset()),
                    timestamp=ExchangeTimestamp(int(order_details.get("T", 0)))
                )
                self._dispatch("liquidation", liq_event)
            except Exception as val_err:
                self.metrics["malformed_messages"] += 1
                logger.warning(f"Discarding invalid liquidation event: {val_err}")

    async def _process_diff_depth(self, symbol: Symbol, data: Dict[str, Any]):
        """Perform contiguity sequence checks on diff depth updates."""
        symbol_str = symbol.value
        first_update_id = int(data.get("U", 0))
        last_update_id = int(data.get("u", 0))
        prev_last_update_id = int(data.get("pu", 0))

        # Check if we are currently syncing snapshot
        if self.book_snapshot_syncing[symbol_str]:
            self.book_buffered_updates[symbol_str].append(data)
            return

        last_known_id = self.last_update_ids[symbol_str]

        # Case 1: First update after initialization/recovery -> sync is required
        if last_known_id == 0:
            logger.info(f"Initial diff depth for {symbol_str}. Launching snapshot synchronization.")
            self.book_snapshot_syncing[symbol_str] = True
            self.book_buffered_updates[symbol_str].append(data)
            asyncio.get_event_loop().create_task(self._recover_order_book_snapshot(symbol))
            return

        # Case 2: Standard check sequence gap check
        # Binance requirement: first_update_id must equal previous last_update_id + 1, OR pu must match previous u.
        # But wait! If we missed messages, we detect a sequence gap!
        if first_update_id > last_known_id + 1:
            logger.warning(f"Sequence gap detected for {symbol_str}! Inbound: {first_update_id}, Last Known: {last_known_id}")
            self.metrics["gap_detections"] += 1
            self.book_snapshot_syncing[symbol_str] = True
            self.book_buffered_updates[symbol_str].append(data)
            asyncio.get_event_loop().create_task(self._recover_order_book_snapshot(symbol))
            return

        # Out-of-order check
        if last_update_id <= last_known_id:
            # Duplicate / stale update, ignore
            return

        # Contiguous update -> emit diff and advance counter
        self.last_update_ids[symbol_str] = last_update_id
        self._dispatch("depth_diff", data)

    async def _recover_order_book_snapshot(self, symbol: Symbol):
        """Fetch REST depth snapshot and fast-forward buffered websocket packets."""
        symbol_str = symbol.value
        rest_symbol = symbol_str.replace("-", "").replace("_", "")
        url = f"{self.rest_url}/fapi/v1/depth?symbol={rest_symbol}&limit=100"
        
        try:
            response = await self.http_client.get(url)
            if response.status_code == 200:
                snap_data = response.json()
                snapshot_last_id = int(snap_data.get("lastUpdateId", 0))
                logger.info(f"Successfully fetched REST depth snapshot for {symbol_str} with update ID {snapshot_last_id}")

                # Dispatch snapshot
                ts = ExchangeTimestamp(int(snap_data.get("E", snap_data.get("T", int(time.time() * 1000)))))
                bids = [
                    OrderBookLevel(Price(Decimal(str(b[0])), symbol), Quantity(Decimal(str(b[1])), symbol.base_asset()))
                    for b in snap_data.get("bids", [])
                ]
                asks = [
                    OrderBookLevel(Price(Decimal(str(a[0])), symbol), Quantity(Decimal(str(a[1])), symbol.base_asset()))
                    for a in snap_data.get("asks", [])
                ]
                snapshot = OrderBookSnapshot(
                    symbol=symbol,
                    timestamp=ts,
                    bids=bids,
                    asks=asks,
                    sequence_id=snapshot_last_id
                )
                self._dispatch("depth_snapshot", snapshot)

                # Process buffered WS packets
                buffered = self.book_buffered_updates[symbol_str]
                self.last_update_ids[symbol_str] = snapshot_last_id
                
                for update in buffered:
                    u_first = int(update.get("U", 0))
                    u_last = int(update.get("u", 0))
                    
                    # 1. Discard updates completely before snapshot
                    if u_last <= snapshot_last_id:
                        continue
                    
                    # 2. First update to apply must cover S + 1
                    # Since we set last_update_ids to snapshot_last_id, standard contiguity checks will apply
                    if u_first <= snapshot_last_id + 1 <= u_last:
                        self.last_update_ids[symbol_str] = u_last
                        self._dispatch("depth_diff", update)
                    elif u_first > self.last_update_ids[symbol_str] + 1:
                        # Gapped again during recovery? This is rare, but force restart if happens
                        logger.warning(f"Re-gapped during recovery for {symbol_str}. Clearing state.")
                        self.last_update_ids[symbol_str] = 0
                        break
                    else:
                        self.last_update_ids[symbol_str] = u_last
                        self._dispatch("depth_diff", update)

                buffered.clear()
            else:
                logger.error(f"Failed to fetch depth snapshot for {symbol_str}: HTTP {response.status_code}")
                # Reset sync state to allow retry on next tick
                self.last_update_ids[symbol_str] = 0
        except Exception as e:
            logger.error(f"Error recovering order book snapshot: {e}")
            self.last_update_ids[symbol_str] = 0
        finally:
            self.book_snapshot_syncing[symbol_str] = False

    async def _poll_open_interest(self):
        """Poll Open Interest from REST endpoints periodically."""
        while self._running:
            try:
                for symbol in self.symbols:
                    if not self._running:
                        break
                    rest_symbol = symbol.value.replace("-", "").replace("_", "")
                    url = f"{self.rest_url}/fapi/v1/openInterest?symbol={rest_symbol}"
                    
                    response = await self.http_client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        oi = OpenInterest(
                            symbol=symbol,
                            value=Quantity(Decimal(str(data.get("openInterest", 0.0))), symbol.base_asset()),
                            timestamp=ExchangeTimestamp(int(data.get("time", int(time.time() * 1000))))
                        )
                        self._dispatch("open_interest", oi)
                    else:
                        logger.warning(f"Failed to poll Open Interest for {symbol.value}: HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"Error polling Open Interest: {e}")

            # Poll interval (e.g. every 10 seconds)
            await asyncio.sleep(10.0)

    def _dispatch(self, stream_type: str, data: Any):
        """Dispatches normalized entities to registered callbacks and passive feeds."""
        # 1. Forward to registered callback
        callback = self.callbacks.get(stream_type)
        if callback:
            try:
                callback(data)
            except Exception as cb_err:
                logger.error(f"Error in subscriber callback for {stream_type}: {cb_err}")

        # 2. Forward trade ticks to active MarketDataFeed instances to sync watch feeds
        if stream_type == "trade":
            try:
                from infrastructure.data.market_data_feed import MarketDataFeed
                for feed in list(MarketDataFeed._active_instances):
                    try:
                        feed.on_trade_tick(data)
                    except Exception as feed_err:
                        logger.error(f"Error updating active MarketDataFeed instance: {feed_err}")
            except Exception as import_err:
                logger.error(f"Error importing MarketDataFeed for dispatch forwarding: {import_err}")
