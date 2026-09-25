"""Feed actual completed bars into existing strategy buffers for one symbol.

This is a deliberately bounded research DataSource adapter, not a strategy or
timeframe proxy. It uses BaseStrategyAdapter.update_with_market_data unchanged.
"""

from datetime import timedelta


_TIMEFRAMES = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}


class CausalStrategyHistoryFeed:
    def __init__(self, strategy_manager, symbol):
        self.strategy_manager = strategy_manager
        self.symbol = str(symbol)
        self._last_close = {}

    def accept(self, bar, decision_time):
        if bar.symbol != self.symbol:
            raise ValueError("one-symbol strategy history scope required")
        if bar.close_time > decision_time:
            raise ValueError("future strategy bar")
        previous = self._last_close.get(bar.timeframe)
        if previous is not None and bar.close_time <= previous:
            raise ValueError("duplicate or out-of-order strategy bar")
        self._last_close[bar.timeframe] = bar.close_time

        payload = {
            "open": bar.open, "high": bar.high, "low": bar.low,
            "close": bar.close, "volume": bar.volume,
            "timestamp": bar.close_time,
        }
        for adapter in self.strategy_manager.strategies.values():
            timeframe = str(adapter.config.get("timeframe", ""))
            if timeframe not in _TIMEFRAMES:
                raise ValueError(f"unsupported strategy timeframe: {timeframe}")
            if _TIMEFRAMES[timeframe] == bar.timeframe:
                adapter.update_with_market_data(payload.copy())
