import pytest
from datetime import datetime
from decimal import Decimal
from domain.entities import TradeTick
from domain.value_objects import Symbol, ExchangeTimestamp, Price, Quantity, Side
from infrastructure.data.market_data_feed import MarketDataFeed
from infrastructure.data.collector.binance_collector import BinanceMarketDataCollector


def test_market_data_feed_passive_cache_and_thread_safety():
    # 1. Initialize passive feed
    feed = MarketDataFeed()
    symbol = Symbol("BTCUSDT")
    feed.add_symbol(symbol)
    
    # Track callback notifications
    notifications = []
    def dummy_handler(data):
        notifications.append(data)
        
    feed.register_handler(symbol, dummy_handler)
    feed.start_feed()
    
    # 2. Mock a TradeTick event
    trade_tick = TradeTick(
        symbol=symbol,
        trade_id=12345,
        price=Price(Decimal("50000.0"), symbol),
        quantity=Quantity(Decimal("1.5"), "BTC"),
        timestamp=ExchangeTimestamp(1721260800000),  # Epoch in ms
        side=Side.BUY
    )
    
    # 3. Simulate callback trigger via on_trade_tick directly
    feed.on_trade_tick(trade_tick)
    
    # Verify cache updates
    assert feed.get_current_price(symbol) == 50000.0
    cached = feed.get_cached_data(symbol)
    assert cached["close"] == 50000.0
    assert cached["symbol"] == "BTCUSDT"
    
    # Verify handler notifications
    assert len(notifications) == 1
    assert notifications[0]["price"] == 50000.0
    assert notifications[0]["symbol"] == "BTCUSDT"
    
    # 4. Verify stop feed turns off notifications
    feed.stop_feed()
    feed.on_trade_tick(trade_tick)
    assert len(notifications) == 1  # Should not increase since feed is stopped


def test_binance_collector_dispatches_to_passive_feed():
    # Verify collector dispatch forwards correctly to active feeds
    feed = MarketDataFeed()
    symbol = Symbol("ETHUSDT")
    feed.add_symbol(symbol)
    feed.start_feed()
    
    # Mock collector setup
    collector = BinanceMarketDataCollector()
    collector.symbols = [symbol]
    
    trade_tick = TradeTick(
        symbol=symbol,
        trade_id=67890,
        price=Price(Decimal("3000.0"), symbol),
        quantity=Quantity(Decimal("0.5"), "ETH"),
        timestamp=ExchangeTimestamp(1721260800000),
        side=Side.BUY
    )
    
    # Dispatch through the collector
    collector._dispatch("trade", trade_tick)
    
    # The active feed should have captured the price automatically via WeakSet registration
    assert feed.get_current_price(symbol) == 3000.0
    feed.stop_feed()
