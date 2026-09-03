"""Boundary mappers — construct canonical domain objects from transport DTOs.

E4.T4 (Phase 1B). This module is the single *choke point* between the transport
layer (``application.dto`` DTOs, pure primitive carriers) and the domain model.
It owns:
- the value-object primitives (``to_symbol``/``to_money``/``to_percentage``/
  ``to_decimal``) that turn raw input into canonical ``domain.value_objects``,
  rejecting invalid input with ``ValueError``/``TypeError``; and
- the entity mappers (``*_to_domain``) that build canonical ``domain.entities``
  from a DTO.

Dependency direction: ``mappers`` depends on ``domain`` (runtime) and on the DTO
classes (type-checking only). DTOs depend on neither — they stay pure transport.
No infrastructure dependencies. No new value objects / domain abstractions.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Union, TYPE_CHECKING

from domain.value_objects import Symbol, Money, Percentage
from domain.entities.market_data import MarketData
from domain.entities.order import Order, Fill
from domain.entities.account import Balance
from domain.entities.position import Position
from domain.enums.order_side import OrderSide
from domain.enums.position_side import PositionSide

if TYPE_CHECKING:  # type-only; avoids any DTO->mapper runtime import cycle
    from application.dto.market_data_dto import MarketDataDTO
    from application.dto.order_dto import OrderDTO, FillDTO
    from application.dto.balance_dto import BalanceDTO
    from application.dto.position_dto import PositionDTO

# Raw numeric inputs accepted at a boundary before coercion to ``Decimal``.
Number = Union[int, float, str, Decimal]


# --------------------------------------------------------------------------- #
# Value-object primitives (the raw -> canonical VO choke point)
# --------------------------------------------------------------------------- #
def to_decimal(raw: Number, field: str = "value") -> Decimal:
    """Coerce a raw numeric input to ``Decimal``; reject non-numeric/None/bool."""
    if raw is None or isinstance(raw, bool):
        raise ValueError(f"{field} must be a number, got {raw!r}")
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} is not a valid number: {raw!r}") from exc


def to_symbol(raw: str) -> Symbol:
    """Build a canonical ``Symbol`` (normalizes case/whitespace; VO validates format)."""
    if not isinstance(raw, str):
        raise TypeError(f"symbol must be a string, got {type(raw).__name__}")
    normalized = raw.strip().upper()
    if not normalized:
        raise ValueError("symbol must be a non-empty string")
    return Symbol(normalized)


def to_money(amount: Number, currency: str) -> Money:
    """Build a canonical ``Money`` (amount -> Decimal; VO validates currency)."""
    if not isinstance(currency, str):
        raise TypeError(f"currency must be a string, got {type(currency).__name__}")
    amount_dec = to_decimal(amount, "amount")
    return Money(amount_dec, currency.strip().upper())


def to_percentage(value: Number) -> Percentage:
    """Build a canonical ``Percentage`` (fraction in [0, 1]; VO enforces range)."""
    return Percentage(to_decimal(value, "percentage"))


# --------------------------------------------------------------------------- #
# Entity mappers (transport DTO -> canonical domain entity)
# --------------------------------------------------------------------------- #
def market_data_to_domain(dto: "MarketDataDTO") -> MarketData:
    """Build the canonical ``MarketData`` entity from a ``MarketDataDTO``.

    ``MarketData`` models prices as ``float`` by design, so numeric fields pass
    through unchanged; only ``symbol`` is promoted to a value object.
    """
    return MarketData(
        symbol=to_symbol(dto.symbol),
        price=dto.price,
        timestamp=dto.timestamp,
        bid=dto.bid,
        ask=dto.ask,
        volume=dto.volume,
        high=dto.high,
        low=dto.low,
        open=dto.open,
        close=dto.close,
    )


def order_to_domain(dto: "OrderDTO") -> Order:
    """Build the canonical ``Order`` entity from an ``OrderDTO``."""
    return Order(
        symbol=to_symbol(dto.symbol),
        side=OrderSide(dto.side.strip().upper()),
        quantity=to_decimal(dto.quantity, "quantity"),
        price=to_money(dto.price, dto.currency) if dto.price is not None else None,
        order_type=dto.order_type,
        client_order_id=dto.client_order_id,
        strategy_name=dto.strategy_name,
        timestamp=dto.timestamp,
    )


def fill_to_domain(dto: "FillDTO") -> Fill:
    """Build the canonical ``Fill`` entity from a ``FillDTO``."""
    return Fill(
        symbol=to_symbol(dto.symbol),
        side=OrderSide(dto.side.strip().upper()),
        quantity=to_decimal(dto.quantity, "quantity"),
        price=to_money(dto.price, dto.currency),
        timestamp=dto.timestamp,
        order_id=dto.order_id,
        fee=to_money(dto.fee, dto.fee_currency or dto.currency),
        fee_currency=dto.fee_currency,
        trade_id=dto.trade_id,
    )


def balance_to_domain(dto: "BalanceDTO") -> Balance:
    """Build the canonical ``Balance`` entity from a ``BalanceDTO``.

    ``Balance.asset`` is a plain asset code (``str``) in the canonical model, so
    it is not promoted to a value object here.
    """
    return Balance(
        asset=dto.asset,
        total=to_decimal(dto.total, "total"),
        available=to_decimal(dto.available, "available"),
        reserved=to_decimal(dto.reserved, "reserved"),
        timestamp=dto.timestamp,
    )


def position_to_domain(dto: "PositionDTO") -> Position:
    """Build the canonical ``Position`` entity from a ``PositionDTO``."""
    return Position(
        symbol=to_symbol(dto.symbol),
        side=PositionSide(dto.side.strip().upper()),
        quantity=to_decimal(dto.quantity, "quantity"),
        entry_price=to_money(dto.entry_price, dto.currency),
        timestamp=dto.timestamp,
        unrealized_pnl=(
            to_money(dto.unrealized_pnl, dto.currency)
            if dto.unrealized_pnl is not None
            else None
        ),
        margin_used=(
            to_money(dto.margin_used, dto.currency)
            if dto.margin_used is not None
            else None
        ),
        strategy_name=dto.strategy_name,
        leverage=getattr(dto, "leverage", None),
        isolated=getattr(dto, "isolated", None),
    )
