"""Unit and integration tests for the Binance Futures Market Data Collector Layer (Milestone 1)."""

import pytest
import asyncio
import json
import httpx
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from domain.value_objects import Symbol, Side
from domain.entities import (
    TradeTick,
    OrderBookSnapshot,
    MarkPrice,
    FundingRate,
    LiquidationEvent,
    OpenInterest,
)
from infrastructure.data.collector.binance_collector import BinanceMarketDataCollector


class MockWebSocket:
    """Mock WebSocket client for simulating stream events."""

    def __init__(self, messages: list):
        self.messages = messages
        self.index = 0
        self.closed = False
        self.close_called = False

    async def recv(self) -> str:
        if self.closed or self.index >= len(self.messages):
            # Block indefinitely to simulate quiet socket
            await asyncio.sleep(3600.0)
            return ""
        
        msg = self.messages[self.index]
        self.index += 1
        return json.dumps(msg)

    async def close(self):
        self.closed = True
        self.close_called = True


class MockHttpClient:
    """Mock httpx.AsyncClient for simulating REST API responses."""

    def __init__(self):
        self.get_calls = []
        self.responses = {}

    def set_response(self, url_prefix: str, status_code: int, json_data: Any):
        self.responses[url_prefix] = (status_code, json_data)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        self.get_calls.append(url)
        for prefix, (status, data) in self.responses.items():
            if prefix in url:
                # Mock httpx Response object
                request = httpx.Request("GET", url)
                return httpx.Response(status, json=data, request=request)
        
        # Default fallback
        request = httpx.Request("GET", url)
        return httpx.Response(404, json={"msg": "Not Found"}, request=request)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collector_successful_normalization_flow():
    """Verify that incoming WebSocket payloads are correctly parsed and normalized."""
    symbol = Symbol("BTC-USDT")
    
    # Pre-defined mock stream messages
    mock_messages = [
        # 1. Trade Tick
        {
            "stream": "btcusdt@trade",
            "data": {
                "e": "trade",
                "E": 1700000000000,
                "s": "BTCUSDT",
                "t": 10001,
                "p": "45000.50",
                "q": "0.150",
                "T": 1700000000000,
                "m": False  # buyer maker flag False -> BUY
            }
        },
        # 2. Mark Price and Funding Rate
        {
            "stream": "btcusdt@markPrice@1s",
            "data": {
                "e": "markPriceUpdate",
                "E": 1700000000100,
                "s": "BTCUSDT",
                "p": "45010.00",
                "r": "0.000100",
                "T": 1700000028800
            }
        },
        # 3. Partial Depth Snapshot (top 5)
        {
            "stream": "btcusdt@depth5@100ms",
            "data": {
                "lastUpdateId": 50000,
                "E": 1700000000200,
                "T": 1700000000200,
                "b": [["44990.0", "1.5"], ["44980.0", "2.0"]],
                "a": [["45020.0", "0.8"], ["45030.0", "1.2"]]
            }
        },
        # 4. Liquidation Event
        {
            "stream": "btcusdt@forceOrder",
            "data": {
                "e": "forceOrder",
                "s": "BTCUSDT",
                "o": {
                    "s": "SELL",
                    "p": "44900.00",
                    "q": "2.50",
                    "T": 1700000000300
                }
            }
        }
    ]

    mock_ws = MockWebSocket(mock_messages)
    mock_http = MockHttpClient()
    
    # Mock REST API response for Open Interest
    mock_http.set_response(
        "openInterest", 
        200, 
        {"symbol": "BTCUSDT", "openInterest": "15000.75", "time": 1700000000000}
    )

    collector = BinanceMarketDataCollector(
        ws_url="mock://ws",
        rest_url="mock://rest",
        http_client=mock_http,  # type: ignore
        ws_client=mock_ws,
        reconnect_delay=0.01,
        heartbeat_interval=1.0
    )

    dispatched = {}

    def get_cb(name):
        def cb(data):
            dispatched[name] = data
        return cb

    callbacks = {
        "trade": get_cb("trade"),
        "mark_price": get_cb("mark_price"),
        "funding": get_cb("funding"),
        "depth_partial": get_cb("depth_partial"),
        "liquidation": get_cb("liquidation"),
        "open_interest": get_cb("open_interest"),
    }

    # Start collection
    collector.start_collecting([symbol], callbacks)
    
    # Wait for the WebSocket messages and REST polling to trigger
    await asyncio.sleep(0.2)
    collector.stop_collecting()

    # Validate Trade
    assert "trade" in dispatched
    t = dispatched["trade"]
    assert isinstance(t, TradeTick)
    assert t.trade_id == 10001
    assert t.price.value == Decimal("45000.50")
    assert t.quantity.value == Decimal("0.150")
    assert t.side == Side.BUY

    # Validate Mark Price
    assert "mark_price" in dispatched
    mp = dispatched["mark_price"]
    assert isinstance(mp, MarkPrice)
    assert mp.price.value == Decimal("45010.00")

    # Validate Funding Rate
    assert "funding" in dispatched
    f = dispatched["funding"]
    assert isinstance(f, FundingRate)
    assert f.rate == Decimal("0.000100")
    assert f.next_funding_time.to_millis() == 1700000028800

    # Validate Partial Depth
    assert "depth_partial" in dispatched
    dp = dispatched["depth_partial"]
    assert isinstance(dp, OrderBookSnapshot)
    assert dp.sequence_id == 50000
    assert len(dp.bids) == 2
    assert dp.bids[0].price.value == Decimal("44990.0")

    # Validate Liquidation
    assert "liquidation" in dispatched
    lq = dispatched["liquidation"]
    assert isinstance(lq, LiquidationEvent)
    assert lq.side == Side.SELL
    assert lq.quantity.value == Decimal("2.50")

    # Validate Open Interest Polling
    assert "open_interest" in dispatched
    oi = dispatched["open_interest"]
    assert isinstance(oi, OpenInterest)
    assert oi.value.value == Decimal("15000.75")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collector_duplicate_trade_filtering():
    """Verify that duplicate trade events are filtered out and metrics updated."""
    symbol = Symbol("BTC-USDT")
    duplicate_messages = [
        # First trade tick
        {
            "stream": "btcusdt@trade",
            "data": {
                "e": "trade", "E": 1700000000000, "s": "BTCUSDT",
                "t": 99999, "p": "45000.0", "q": "1.0", "T": 1700000000000, "m": False
            }
        },
        # Identical duplicate trade tick
        {
            "stream": "btcusdt@trade",
            "data": {
                "e": "trade", "E": 1700000000000, "s": "BTCUSDT",
                "t": 99999, "p": "45000.0", "q": "1.0", "T": 1700000000000, "m": False
            }
        }
    ]

    mock_ws = MockWebSocket(duplicate_messages)
    mock_http = MockHttpClient()
    mock_http.set_response("openInterest", 404, {}) # Skip OI

    collector = BinanceMarketDataCollector(
        ws_url="mock://ws", rest_url="mock://rest",
        http_client=mock_http, ws_client=mock_ws, # type: ignore
        reconnect_delay=0.01
    )

    trade_calls = []
    collector.start_collecting([symbol], {"trade": lambda t: trade_calls.append(t)})
    
    await asyncio.sleep(0.1)
    collector.stop_collecting()

    # Verify only 1 trade tick was dispatched
    assert len(trade_calls) == 1
    assert collector.get_metrics()["duplicate_messages"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collector_sequence_gap_detection_and_rest_recovery():
    """Verify that sequence gaps in diff depth updates trigger REST snapshot synchronization."""
    symbol = Symbol("BTC-USDT")
    
    diff_depth_messages = [
        # 1. Initial diff depth -> registers last_known_id = 100
        {
            "stream": "btcusdt@depth@100ms",
            "data": {
                "e": "depthUpdate", "E": 1700000000000, "s": "BTCUSDT",
                "U": 50, "u": 100, "pu": 49,
                "b": [], "a": []
            }
        },
        # 2. Gapped update -> first ID is 150 (gapped relative to 100) -> triggers REST sync
        {
            "stream": "btcusdt@depth@100ms",
            "data": {
                "e": "depthUpdate", "E": 1700000000100, "s": "BTCUSDT",
                "U": 150, "u": 200, "pu": 149,
                "b": [], "a": []
            }
        }
    ]

    mock_ws = MockWebSocket(diff_depth_messages)
    mock_http = MockHttpClient()
    mock_http.set_response("openInterest", 404, {})
    
    # Mock REST depth snapshot response (lastUpdateId = 160)
    mock_http.set_response(
        "depth",
        200,
        {
            "lastUpdateId": 160,
            "bids": [["45000.0", "1.0"]],
            "asks": [["45010.0", "1.0"]]
        }
    )

    collector = BinanceMarketDataCollector(
        ws_url="mock://ws", rest_url="mock://rest",
        http_client=mock_http, ws_client=mock_ws, # type: ignore
        reconnect_delay=0.01
    )

    events = []
    callbacks = {
        "depth_snapshot": lambda s: events.append(("snapshot", s)),
        "depth_diff": lambda d: events.append(("diff", d))
    }

    collector.start_collecting([symbol], callbacks)
    
    # Pre-set last update ID to 100 to trigger a sequence gap check on U=150
    collector.last_update_ids[symbol.value] = 100
    collector.book_snapshot_syncing[symbol.value] = False
    
    await asyncio.sleep(0.3)
    collector.stop_collecting()

    # Gap metrics should increment
    metrics = collector.get_metrics()
    assert metrics["gap_detections"] >= 1

    # Should have a REST snapshot recovery GET call
    assert any("depth" in url for url in mock_http.get_calls)

    # Check dispatched events sequence:
    # 1. First initial diff (dispatched because it is the first before gap)
    # 2. REST snapshot (sequence_id = 160)
    # 3. Fast-forwarded diff (u=200 > 160)
    assert len(events) >= 2
    event_types = [ev[0] for ev in events]
    assert "snapshot" in event_types


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collector_malformed_message_rejection():
    """Verify that malformed payloads are safely rejected without throwing exceptions."""
    symbol = Symbol("BTC-USDT")
    bad_messages = [
        # Bad JSON format
        "invalid-json-string-here",
        # Missing event type
        {"stream": "btcusdt@trade", "data": {"s": "BTCUSDT"}},
        # Missing symbol
        {"stream": "btcusdt@trade", "data": {"e": "trade", "t": 123}}
    ]

    # Pre-encode list containing malformed string
    class StringMockWebSocket(MockWebSocket):
        async def recv(self) -> str:
            if self.closed or self.index >= len(self.messages):
                await asyncio.sleep(3600.0)
                return ""
            msg = self.messages[self.index]
            self.index += 1
            return msg if isinstance(msg, str) else json.dumps(msg)

    mock_ws = StringMockWebSocket(bad_messages)
    mock_http = MockHttpClient()
    mock_http.set_response("openInterest", 404, {})

    collector = BinanceMarketDataCollector(
        ws_url="mock://ws", rest_url="mock://rest",
        http_client=mock_http, ws_client=mock_ws, # type: ignore
        reconnect_delay=0.01
    )

    collector.start_collecting([symbol], {})
    await asyncio.sleep(0.1)
    collector.stop_collecting()

    metrics = collector.get_metrics()
    # At least 1 malformed JSON message, and other validation errors
    assert metrics["malformed_messages"] + metrics["malformed_messages"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collector_heartbeat_timeout_reconnect():
    """Verify heartbeat timeout forces reconnect delays."""
    symbol = Symbol("BTC-USDT")
    
    # Send nothing to trigger heartbeat timeout
    mock_ws = MockWebSocket([])
    mock_http = MockHttpClient()
    mock_http.set_response("openInterest", 404, {})

    collector = BinanceMarketDataCollector(
        ws_url="mock://ws", rest_url="mock://rest",
        http_client=mock_http, ws_client=mock_ws, # type: ignore
        reconnect_delay=0.01,
        heartbeat_interval=0.05 # Tiny interval to trigger timeout quickly
    )

    collector.start_collecting([symbol], {})
    
    # Wait for heartbeat monitor to fire and force close
    await asyncio.sleep(0.15)
    collector.stop_collecting()

    # Reconnect count should have been incremented
    assert collector.get_metrics()["heartbeat_failures"] >= 1
    assert mock_ws.close_called is True
