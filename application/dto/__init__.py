"""Application DTO layer (E4.T4).

Pure transport DTOs + the boundary mapper module. DTOs carry only primitives
and have no domain knowledge; ``application.dto.mappers`` is the single choke
point that converts DTOs into canonical domain entities and constructs the
domain value objects (``Symbol``/``Money``/``Percentage``), rejecting invalid
raw input at the edge.

Phase 1B: DTOs + mappers only — NOT yet wired into live boundaries (Phase 2).
"""

from application.dto.mappers import (
    # value-object primitives (raw -> canonical VO)
    to_symbol,
    to_money,
    to_percentage,
    to_decimal,
    # entity mappers (transport DTO -> canonical domain entity)
    market_data_to_domain,
    order_to_domain,
    fill_to_domain,
    balance_to_domain,
    position_to_domain,
)
from application.dto.market_data_dto import MarketDataDTO
from application.dto.order_dto import OrderDTO, FillDTO
from application.dto.balance_dto import BalanceDTO
from application.dto.position_dto import PositionDTO

__all__ = [
    # value-object primitives
    "to_symbol",
    "to_money",
    "to_percentage",
    "to_decimal",
    # entity mappers
    "market_data_to_domain",
    "order_to_domain",
    "fill_to_domain",
    "balance_to_domain",
    "position_to_domain",
    # DTOs (pure transport)
    "MarketDataDTO",
    "OrderDTO",
    "FillDTO",
    "BalanceDTO",
    "PositionDTO",
]
