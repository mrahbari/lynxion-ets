"""Thin transport DTOs for inbound/outbound orders and fills (E4.T4 Phase 1B).

Pure primitive carriers mirroring external order/fill payloads. No domain
knowledge and no conversion logic — DTO->domain conversion lives in
``application.dto.mappers`` (``order_to_domain`` / ``fill_to_domain``).
Not yet wired into live boundaries (Phase 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

# Raw numeric inputs accepted at the boundary (coerced to Decimal by the mapper).
Number = Union[int, float, str, Decimal]


@dataclass(frozen=True)
class OrderDTO:
    """Raw order request/response (primitives only)."""

    symbol: str
    side: str
    quantity: Number
    price: Optional[Number] = None
    currency: str = "USD"
    order_type: str = "MARKET"
    client_order_id: Optional[str] = None
    strategy_name: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class FillDTO:
    """Raw trade fill (primitives only)."""

    symbol: str
    side: str
    quantity: Number
    price: Number
    timestamp: datetime
    order_id: str
    fee: Number = 0
    currency: str = "USD"
    fee_currency: str = ""
    trade_id: Optional[str] = None
