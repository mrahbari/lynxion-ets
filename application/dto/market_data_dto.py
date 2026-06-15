"""Thin transport DTO for inbound market-data rows (E4.T4 Phase 1B).

Pure primitive carrier mirroring an external OHLCV/quote row. No domain
knowledge and no conversion logic — DTO->domain conversion lives in
``application.dto.mappers.market_data_to_domain``. Not yet wired (Phase 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class MarketDataDTO:
    """Raw market-data row as received at a data boundary (primitives only)."""

    symbol: str
    price: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
