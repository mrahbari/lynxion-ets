from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from domain.value_objects import Symbol, Price, Quantity, ExchangeTimestamp
from domain.entities import OrderBookLevel, OrderBookSnapshot


class SequenceGapError(Exception):
    """Exception raised when a sequence number contiguity gap is detected in diff updates."""
    pass


@dataclass
class OrderBookState:
    """Canonical in-memory representation of a Level 2 Order Book state."""
    symbol: Symbol
    bids: Dict[Decimal, Decimal] = field(default_factory=dict)  # price -> qty
    asks: Dict[Decimal, Decimal] = field(default_factory=dict)  # price -> qty
    last_update_id: int = 0
    timestamp: Optional[ExchangeTimestamp] = None

    def get_best_bid(self) -> Optional[Decimal]:
        """Return the best bid price level."""
        if not self.bids:
            return None
        return max(self.bids.keys())

    def get_best_ask(self) -> Optional[Decimal]:
        """Return the best ask price level."""
        if not self.asks:
            return None
        return min(self.asks.keys())

    def get_spread(self) -> Optional[Decimal]:
        """Return the spread between best ask and best bid."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid is None or best_ask is None:
            return None
        return best_ask - best_bid

    def get_mid_price(self) -> Optional[Decimal]:
        """Return the mid price."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid is None or best_ask is None:
            return None
        return (best_bid + best_ask) / Decimal("2")

    def get_depth(self, depth: int) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """Return top N bids (descending) and asks (ascending) as sorted (price, qty) lists."""
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:depth]
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])[:depth]
        return sorted_bids, sorted_asks

    def to_snapshot(self) -> OrderBookSnapshot:
        """Serialize state back into a canonical OrderBookSnapshot entity."""
        best_bids, best_asks = self.get_depth(100) # Default cap at top 100 levels
        
        bids_levels = [
            OrderBookLevel(Price(p, self.symbol), Quantity(q, self.symbol.base_asset()))
            for p, q in best_bids
        ]
        asks_levels = [
            OrderBookLevel(Price(p, self.symbol), Quantity(q, self.symbol.base_asset()))
            for p, q in best_asks
        ]
        
        return OrderBookSnapshot(
            symbol=self.symbol,
            timestamp=self.timestamp or ExchangeTimestamp(int(datetime.now().timestamp() * 1000)),
            bids=bids_levels,
            asks=asks_levels,
            sequence_id=self.last_update_id
        )

    def calculate_checksum(self) -> int:
        """Calculate a deterministic checksum representing the current top 10 bids/asks."""
        # Custom checksum combining top bids & asks prices and quantities
        bids, asks = self.get_depth(10)
        checksum_str = ""
        for p, q in bids:
            checksum_str += f"{p}:{q}:"
        checksum_str += "|"
        for p, q in asks:
            checksum_str += f"{p}:{q}:"
        return hash(checksum_str)


class OrderBookBuilder:
    """Reconstruction engine for reconstructing order books from diff updates."""

    def __init__(self, symbol: Symbol):
        self.symbol = symbol
        self.state = OrderBookState(symbol=symbol)
        self.is_initialized = False

    def apply_snapshot(self, snapshot: OrderBookSnapshot) -> None:
        """Initialize the order book state with a full snapshot."""
        if snapshot.symbol != self.symbol:
            raise ValueError(f"Symbol mismatch: snapshot symbol {snapshot.symbol} does not match engine {self.symbol}")

        self.state.bids.clear()
        self.state.asks.clear()

        # Load bids
        for level in snapshot.bids:
            self._update_level(self.state.bids, level.price.value, level.quantity.value)

        # Load asks
        for level in snapshot.asks:
            self._update_level(self.state.asks, level.price.value, level.quantity.value)

        self.state.last_update_id = snapshot.sequence_id
        self.state.timestamp = snapshot.timestamp
        
        # Check invariants after snapshot load
        self._validate_invariants()
        self.is_initialized = True

    def apply_diff(self, diff_event: Dict[str, Any]) -> None:
        """Apply a normalized diff depth update to the order book.
        
        Expects keys:
        - "U": first update ID in this event
        - "u": last update ID in this event
        - "pu": previous last update ID
        - "b": list of bids as [price_str, qty_str]
        - "a": list of asks as [price_str, qty_str]
        - "E": event time (optional)
        """
        if not self.is_initialized:
            raise ValueError("Engine is not initialized; apply a snapshot first.")

        first_update_id = int(diff_event.get("U", 0))
        last_update_id = int(diff_event.get("u", 0))
        prev_last_update_id = int(diff_event.get("pu", 0))

        # 1. Stale update check
        if last_update_id <= self.state.last_update_id:
            # Stale update, discard safely
            return

        # 2. Sequence gap checks
        # If U is greater than last_update_id + 1, OR if pu does not match last_update_id
        if first_update_id > self.state.last_update_id + 1:
            raise SequenceGapError(
                f"Sequence gap detected! Expected U <= {self.state.last_update_id + 1}, got U = {first_update_id}"
            )
        if prev_last_update_id != 0 and prev_last_update_id != self.state.last_update_id:
            # Check if U matches (some feeds don't populate pu or use U as boundary check)
            if first_update_id > self.state.last_update_id + 1:
                raise SequenceGapError(
                    f"Sequence gap detected! Expected pu = {self.state.last_update_id}, got pu = {prev_last_update_id}"
                )

        # 3. Apply updates
        event_timestamp = diff_event.get("E")
        if event_timestamp:
            self.state.timestamp = ExchangeTimestamp(int(event_timestamp))

        # Apply bids
        for b in diff_event.get("b", []):
            price = Decimal(str(b[0]))
            qty = Decimal(str(b[1]))
            self._update_level(self.state.bids, price, qty)

        # Apply asks
        for a in diff_event.get("a", []):
            price = Decimal(str(a[0]))
            qty = Decimal(str(a[1]))
            self._update_level(self.state.asks, price, qty)

        # Update last sequence tracker
        self.state.last_update_id = last_update_id

        # 4. Check invariants
        self._validate_invariants()

    def _update_level(self, levels: Dict[Decimal, Decimal], price: Decimal, qty: Decimal) -> None:
        """Insert, update, or delete a level."""
        if price <= 0:
            raise ValueError(f"Invalid price: Price must be positive, got {price}")
        if qty < 0:
            raise ValueError(f"Invalid quantity: Quantity cannot be negative, got {qty}")

        if qty == 0:
            levels.pop(price, None)
        else:
            levels[price] = qty

    def _validate_invariants(self) -> None:
        """Assert order book invariants (e.g. non-crossing bids/asks)."""
        best_bid = self.state.get_best_bid()
        best_ask = self.state.get_best_ask()
        if best_bid is not None and best_ask is not None:
            if best_bid >= best_ask:
                raise ValueError(f"Crossed order book detected! Best Bid: {best_bid} >= Best Ask: {best_ask}")
