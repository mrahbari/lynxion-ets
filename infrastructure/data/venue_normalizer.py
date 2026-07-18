from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from domain.ports.data_ports import MarketDataNormalizerPort
from domain.value_objects import (
    Symbol,
    ExchangeVenue,
    Price,
    Quantity,
    Side,
    ExchangeTimestamp,
)
from domain.entities import (
    TradeTick,
    OrderBookLevel,
    OrderBookSnapshot,
    SymbolMapping,
)


class VenueMarketDataNormalizer(MarketDataNormalizerPort):
    """Normalizes raw exchange messages from various venues into canonical domain formats."""

    def __init__(self, mappings: Optional[List[SymbolMapping]] = None):
        # Local cache of mappings
        self._mappings: List[SymbolMapping] = mappings or []

    def add_mapping(self, mapping: SymbolMapping):
        """Register a new symbol translation mapping."""
        self._mappings.append(mapping)

    def normalize_symbol(self, raw_symbol: str, venue: ExchangeVenue) -> Symbol:
        """Translate venue-specific symbol strings into canonical Symbols."""
        # 1. Check if we have an explicit SymbolMapping registered
        for mapping in self._mappings:
            if venue == mapping.source_venue and raw_symbol.upper() == mapping.source_symbol.upper():
                # Extract canonical format (we assume canonical maps to standard base-quote representation)
                return Symbol(mapping.source_symbol)
            if venue == mapping.execution_venue and raw_symbol.upper() == mapping.execution_symbol.upper():
                return Symbol(mapping.execution_symbol)

        # 2. Heuristics fallback
        # Binance format: BTCUSDT -> BTC-USDT
        if venue == ExchangeVenue.BINANCE_FUTURES:
            # Simple conversion heuristic for major assets: BTCUSDT -> BTC-USDT
            clean = raw_symbol.upper()
            if clean.endswith("USDT") and len(clean) > 4:
                return Symbol(f"{clean[:-4]}-USDT")
            elif clean.endswith("BUSD") and len(clean) > 4:
                return Symbol(f"{clean[:-4]}-BUSD")
            return Symbol(clean)

        # BingX format: BTC-USDT or BTCUSDT
        if venue == ExchangeVenue.BINGX_FUTURES:
            clean = raw_symbol.upper()
            if "-" in clean:
                return Symbol(clean)
            if clean.endswith("USDT") and len(clean) > 4:
                return Symbol(f"{clean[:-4]}-USDT")
            return Symbol(clean)

        # Default fallback
        return Symbol(raw_symbol)

    def normalize_trade(self, raw_message: Dict[str, Any], venue: ExchangeVenue) -> TradeTick:
        """Normalize raw exchange trade message into a canonical TradeTick."""
        try:
            if venue == ExchangeVenue.BINANCE_FUTURES:
                # Binance WebSocket Trade Stream Payload
                raw_sym = raw_message.get("s", "")
                symbol = self.normalize_symbol(raw_sym, venue)
                trade_id = int(raw_message.get("t", 0))
                price_val = Decimal(str(raw_message.get("p", 0.0)))
                qty_val = Decimal(str(raw_message.get("q", 0.0)))
                ts_val = int(raw_message.get("T", 0))
                # m=True means buyer maker -> sell aggressor
                side = Side.SELL if raw_message.get("m") else Side.BUY

                return TradeTick(
                    symbol=symbol,
                    trade_id=trade_id,
                    price=Price(price_val, symbol),
                    quantity=Quantity(qty_val, symbol.base_asset()),
                    timestamp=ExchangeTimestamp(ts_val),
                    side=side
                )

            elif venue == ExchangeVenue.BINGX_FUTURES:
                # BingX API Trade Payload
                # {"symbol": "BTC-USDT", "price": "45000.0", "volume": "0.1", "time": 1700000000000, "side": "BUY", "tradeId": 123}
                raw_sym = raw_message.get("symbol", "")
                symbol = self.normalize_symbol(raw_sym, venue)
                trade_id = int(raw_message.get("tradeId", raw_message.get("id", 0)))
                price_val = Decimal(str(raw_message.get("price", 0.0)))
                qty_val = Decimal(str(raw_message.get("volume", raw_message.get("qty", 0.0))))
                ts_val = int(raw_message.get("time", 0))
                raw_side = str(raw_message.get("side", "BUY")).upper()
                side = Side.BUY if raw_side == "BUY" else Side.SELL

                return TradeTick(
                    symbol=symbol,
                    trade_id=trade_id,
                    price=Price(price_val, symbol),
                    quantity=Quantity(qty_val, symbol.base_asset()),
                    timestamp=ExchangeTimestamp(ts_val),
                    side=side
                )

            else:
                raise NotImplementedError(f"Normalization for venue {venue} not implemented")

        except Exception as err:
            raise ValueError(f"Failed to normalize trade message: {err}") from err

    def normalize_order_book(self, raw_message: Dict[str, Any], venue: ExchangeVenue) -> OrderBookSnapshot:
        """Normalize raw exchange order book snapshot/diff into a canonical OrderBookSnapshot."""
        try:
            if venue == ExchangeVenue.BINANCE_FUTURES:
                # Binance WebSocket Depth payload or REST snapshot
                # Support both ws "data" (having s, E, bids/asks) or REST format (lastUpdateId, bids, asks)
                raw_sym = raw_message.get("s", "")
                if not raw_sym and "symbol" in raw_message:
                    raw_sym = raw_message.get("symbol", "")
                
                symbol = self.normalize_symbol(raw_sym, venue)
                ts_val = int(raw_message.get("E", raw_message.get("T", int(datetime.now(timezone.utc).timestamp() * 1000))))
                seq_id = int(raw_message.get("lastUpdateId", raw_message.get("u", 0)))

                bids = [
                    OrderBookLevel(Price(Decimal(str(b[0])), symbol), Quantity(Decimal(str(b[1])), symbol.base_asset()))
                    for b in raw_message.get("bids", raw_message.get("b", []))
                ]
                asks = [
                    OrderBookLevel(Price(Decimal(str(a[0])), symbol), Quantity(Decimal(str(a[1])), symbol.base_asset()))
                    for a in raw_message.get("asks", raw_message.get("a", []))
                ]

                return OrderBookSnapshot(
                    symbol=symbol,
                    timestamp=ExchangeTimestamp(ts_val),
                    bids=bids,
                    asks=asks,
                    sequence_id=seq_id
                )

            elif venue == ExchangeVenue.BINGX_FUTURES:
                # BingX order book format
                # {"symbol": "BTC-USDT", "ts": 1700000000000, "bids": [["45000", "1.2"]], "asks": [["45010", "0.5"]]}
                raw_sym = raw_message.get("symbol", "")
                symbol = self.normalize_symbol(raw_sym, venue)
                ts_val = int(raw_message.get("ts", raw_message.get("time", int(datetime.now(timezone.utc).timestamp() * 1000))))
                seq_id = int(raw_message.get("seq", raw_message.get("updateId", 0)))

                bids = [
                    OrderBookLevel(Price(Decimal(str(b[0])), symbol), Quantity(Decimal(str(b[1])), symbol.base_asset()))
                    for b in raw_message.get("bids", [])
                ]
                asks = [
                    OrderBookLevel(Price(Decimal(str(a[0])), symbol), Quantity(Decimal(str(a[1])), symbol.base_asset()))
                    for a in raw_message.get("asks", [])
                ]

                return OrderBookSnapshot(
                    symbol=symbol,
                    timestamp=ExchangeTimestamp(ts_val),
                    bids=bids,
                    asks=asks,
                    sequence_id=seq_id
                )

            else:
                raise NotImplementedError(f"Normalization for venue {venue} not implemented")

        except Exception as err:
            raise ValueError(f"Failed to normalize order book: {err}") from err
