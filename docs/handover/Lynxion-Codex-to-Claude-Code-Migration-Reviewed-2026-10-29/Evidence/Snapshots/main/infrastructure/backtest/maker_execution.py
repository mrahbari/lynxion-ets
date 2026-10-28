"""Declared offline trade-through model; a simulated fill is never broker evidence."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

MODEL = 'CONSERVATIVE_TRADE_THROUGH_V1'


def _clock(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError('explicit timezone-aware clock required')
    return value


def _number(value, *, zero=False):
    if isinstance(value, bool):
        raise ValueError('boolean is not a market number')
    value = Decimal(str(value))
    if not value.is_finite() or value < 0 or (not zero and value == 0):
        raise ValueError('finite positive market number required')
    return value


@dataclass(frozen=True)
class MakerQuote:
    symbol: str
    available_at: datetime
    bid: Decimal
    ask: Decimal
    bid_quantity: Decimal
    ask_quantity: Decimal
    source_id: str

    def __post_init__(self):
        _clock(self.available_at)
        for name in ('bid', 'ask', 'bid_quantity', 'ask_quantity'):
            object.__setattr__(self, name, _number(getattr(self, name), zero='quantity' in name))
        if not self.symbol or not self.source_id or self.bid >= self.ask:
            raise ValueError('explicit symbol/source and uncrossed quote required')


@dataclass(frozen=True)
class MakerTrade:
    symbol: str
    available_at: datetime
    price: Decimal
    quantity: Decimal
    aggressor_side: str
    source_id: str

    def __post_init__(self):
        _clock(self.available_at)
        for name in ('price', 'quantity'):
            object.__setattr__(self, name, _number(getattr(self, name)))
        if not self.symbol or not self.source_id or self.aggressor_side not in ('BUY', 'SELL'):
            raise ValueError('explicit trade symbol/source/aggressor required')


@dataclass(frozen=True)
class MakerFill:
    order_id: str
    symbol: str
    side: str
    available_at: datetime
    price: Decimal
    quantity: Decimal
    fee: Decimal
    source_trade_id: str
    model: str = MODEL


class PendingMakerOrder:
    """One order's explicit modeled queue, partial fills, expiry and cancellation.

    Queue ahead is fixed visible arrival quantity, with no assumed cancellation or
    replenishment. This is a modeling assumption, not a known position in a real queue.
    Portfolio admission and shared volume across simultaneous orders are caller gates.
    """

    def __init__(self, *, order_id, symbol, side, quantity, limit_price, decision_at,
                 quote, latency=timedelta(milliseconds=100), ttl=timedelta(seconds=60),
                 participation=Decimal('0.01'), maker_fee_bps=Decimal('2'),
                 max_quote_age=timedelta(seconds=1)):
        self.decision_at = _clock(decision_at)
        if (not isinstance(latency, timedelta) or latency < timedelta(0) or
                not isinstance(ttl, timedelta) or ttl <= timedelta(0) or
                not isinstance(max_quote_age, timedelta) or max_quote_age < timedelta(0)):
            raise ValueError('invalid explicit latency/TTL/quote age')
        self.arrival_at = decision_at + latency
        self.expires_at = self.arrival_at + ttl
        self.order_id, self.symbol, self.side = order_id, symbol, side
        if not order_id or not symbol or side not in ('BUY', 'SELL'):
            raise ValueError('explicit order identity/symbol/side required')
        self.quantity = self.remaining = _number(quantity)
        self.limit_price = _number(limit_price)
        self.participation = _number(participation)
        self.maker_fee_bps = _number(maker_fee_bps, zero=True)
        if self.participation > 1:
            raise ValueError('participation must not exceed one')
        if not isinstance(quote, MakerQuote) or quote.symbol != symbol:
            raise ValueError('matching observed arrival quote required')
        if quote.available_at > self.arrival_at:
            raise ValueError('future quote cannot admit order')
        if self.arrival_at - quote.available_at > max_quote_age:
            raise ValueError('stale arrival quote')
        self._last_clock = self.arrival_at
        self._seen_trades = {}
        self.fills = []
        self.status = 'RESTING'
        self.queue_ahead = quote.bid_quantity if side == 'BUY' else quote.ask_quantity
        if ((side == 'BUY' and self.limit_price >= quote.ask) or
                (side == 'SELL' and self.limit_price <= quote.bid)):
            self.status = 'REJECTED_POST_ONLY'
        elif self.limit_price != (quote.bid if side == 'BUY' else quote.ask):
            self.status = 'REJECTED_UNSUPPORTED_LIMIT'

    @property
    def active(self):
        return self.status in ('RESTING', 'PARTIALLY_FILLED')

    def on_trade(self, trade):
        if not isinstance(trade, MakerTrade) or trade.symbol != self.symbol:
            raise ValueError('matching typed trade required')
        prior = self._seen_trades.get(trade.source_id)
        if prior is not None:
            if prior != trade:
                raise ValueError('conflicting duplicate trade identity')
            return None
        if trade.available_at <= self.arrival_at:
            return None
        if trade.available_at < self._last_clock:
            raise ValueError('out-of-order event cannot alter queue')
        self._seen_trades[trade.source_id] = trade
        self._last_clock = trade.available_at
        if not self.active:
            return None
        if trade.available_at >= self.expires_at:
            self.status = 'EXPIRED'
            return None
        opposite = 'SELL' if self.side == 'BUY' else 'BUY'
        eligible = trade.price <= self.limit_price if self.side == 'BUY' else trade.price >= self.limit_price
        if trade.aggressor_side != opposite or not eligible:
            return None
        consumed = min(self.queue_ahead, trade.quantity)
        self.queue_ahead -= consumed
        through = trade.price < self.limit_price if self.side == 'BUY' else trade.price > self.limit_price
        if not through:
            return None
        size = min(self.remaining, (trade.quantity - consumed) * self.participation)
        if size <= 0:
            return None
        fill = MakerFill(self.order_id, self.symbol, self.side, trade.available_at,
                         self.limit_price, size, self.limit_price * size * self.maker_fee_bps / 10000,
                         trade.source_id)
        self.remaining -= size
        self.fills.append(fill)
        self.status = 'FILLED' if self.remaining == 0 else 'PARTIALLY_FILLED'
        return fill

    def cancel(self, at):
        at = _clock(at)
        if at < self._last_clock:
            raise ValueError('retroactive cancellation denied')
        self._last_clock = at
        if self.active:
            self.status = 'EXPIRED' if at >= self.expires_at else 'CANCELLED'

    def expire(self, at):
        at = _clock(at)
        if at < self._last_clock:
            raise ValueError('out-of-order expiration')
        self._last_clock = at
        if self.active and at >= self.expires_at:
            self.status = 'EXPIRED'
