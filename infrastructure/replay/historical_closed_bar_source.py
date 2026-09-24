"""Strict completed-bar source; never manufactures watcher observations."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Iterable, Iterator, Tuple


@dataclass(frozen=True)
class ClosedBar:
    symbol: str
    timeframe: timedelta
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoricalClosedBarSource:
    """Validate a frozen input stream and expose only completed events in event time.

    This is deliberately not a MarketObservation factory: that would silently
    substitute candle heuristics for the enabled live watcher universe.
    """

    def __init__(self, bars: Iterable[ClosedBar]):
        ordered = tuple(bars)
        last_close = {}
        for bar in ordered:
            if not bar.symbol or bar.timeframe <= timedelta(0):
                raise ValueError("symbol and positive timeframe required")
            if bar.open_time.tzinfo is None or bar.close_time.tzinfo is None:
                raise ValueError("timezone-aware UTC timestamps required")
            if bar.open_time.utcoffset() != timedelta(0) or bar.close_time.utcoffset() != timedelta(0):
                raise ValueError("timestamps must be UTC")
            if bar.close_time - bar.open_time != bar.timeframe:
                raise ValueError("bar close must equal open plus timeframe")
            if not all(isfinite(x) for x in (bar.open, bar.high, bar.low, bar.close, bar.volume)):
                raise ValueError("nonfinite OHLCV")
            if min(bar.open, bar.high, bar.low, bar.close) <= 0 or bar.volume < 0:
                raise ValueError("invalid OHLCV")
            if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
                raise ValueError("inconsistent OHLC")
            key = (bar.symbol, bar.timeframe)
            previous = last_close.get(key)
            if previous is not None:
                if bar.close_time <= previous:
                    raise ValueError("duplicate or out-of-order close timestamp")
                if bar.open_time != previous:
                    raise ValueError("historical gap or overlap")
            last_close[key] = bar.close_time
        if any(ordered[i].close_time > ordered[i + 1].close_time for i in range(len(ordered) - 1)):
            raise ValueError("global event-time order required")
        self._bars: Tuple[ClosedBar, ...] = ordered

    def completed_through(self, decision_time: datetime) -> Iterator[ClosedBar]:
        if decision_time.tzinfo is None or decision_time.utcoffset() != timedelta(0):
            raise ValueError("UTC decision time required")
        for bar in self._bars:
            if bar.close_time > decision_time:
                break
            yield bar
