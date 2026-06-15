"""Thin transport DTO for inbound positions (E4.T4 Phase 1B).

Pure primitive carrier mirroring an external position payload. No domain
knowledge and no conversion logic — DTO->domain conversion lives in
``application.dto.mappers.position_to_domain``. Not yet wired (Phase 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

# Raw numeric inputs accepted at the boundary (coerced to Decimal by the mapper).
Number = Union[int, float, str, Decimal]


@dataclass(frozen=True)
class PositionDTO:
    """Raw open position as received at a broker boundary (primitives only)."""

    symbol: str
    side: str
    quantity: Number
    entry_price: Number
    timestamp: datetime
    currency: str = "USD"
    unrealized_pnl: Optional[Number] = None
    margin_used: Optional[Number] = None
    strategy_name: Optional[str] = None
