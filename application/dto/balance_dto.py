"""Thin transport DTO for inbound account balances (E4.T4 Phase 1B).

Pure primitive carrier mirroring an external balance payload. No domain
knowledge and no conversion logic — DTO->domain conversion lives in
``application.dto.mappers.balance_to_domain``. Not yet wired (Phase 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Union

# Raw numeric inputs accepted at the boundary (coerced to Decimal by the mapper).
Number = Union[int, float, str, Decimal]


@dataclass(frozen=True)
class BalanceDTO:
    """Raw account balance as received at a broker boundary (primitives only)."""

    asset: str
    total: Number
    available: Number
    reserved: Number
    timestamp: datetime
