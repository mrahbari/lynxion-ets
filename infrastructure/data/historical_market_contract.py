"""Fail-closed market identity for external historical candle requests."""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class MarketType(str, Enum):
    SPOT = "spot"
    PERPETUAL = "perpetual"


@dataclass(frozen=True)
class HistoricalMarketRequest:
    source: str
    market_type: MarketType
    symbol: str
    timeframe: str

    def __post_init__(self) -> None:
        if not isinstance(self.market_type, MarketType):
            raise TypeError("market_type must be an explicit MarketType")
        if not self.source or not self.symbol or not self.timeframe:
            raise ValueError("source, symbol, and timeframe are required")

    @property
    def cache_identity(self) -> Tuple[str, str, str, str]:
        return (
            self.source.strip().lower(),
            self.market_type.value,
            self.symbol.strip().upper(),
            self.timeframe,
        )


_VERIFIED_ENDPOINTS = {
    ("binance", MarketType.SPOT): "https://api.binance.com/api/v3/klines",
    ("binance", MarketType.PERPETUAL): "https://fapi.binance.com/fapi/v1/klines",
}


def verified_candle_endpoint(request: HistoricalMarketRequest) -> str:
    """Return only a frozen, verified source/market mapping; never cross markets."""

    key = (request.source.strip().lower(), request.market_type)
    try:
        return _VERIFIED_ENDPOINTS[key]
    except KeyError as exc:
        raise ValueError(
            f"unsupported historical market mapping: {key[0]}/{key[1].value}"
        ) from exc
