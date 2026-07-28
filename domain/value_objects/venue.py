from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, Any


class ExchangeVenue(Enum):
    """Supported market and execution venues."""
    BINANCE_FUTURES = "BINANCE_FUTURES"
    BINGX_FUTURES = "BINGX_FUTURES"
    MEXC_FUTURES = "MEXC_FUTURES"
    PHEMEX_FUTURES = "PHEMEX_FUTURES"
    HISTORICAL_PROVIDER = "HISTORICAL_PROVIDER"


class MarketType(Enum):
    """Classification of markets."""
    SPOT = "SPOT"
    FUTURES = "FUTURES"


class ContractType(Enum):
    """Symmetric classification of contract instruments."""
    SPOT = "SPOT"
    PERPETUAL = "PERPETUAL"
    FUTURES = "FUTURES"
    INVERSE_PERPETUAL = "INVERSE_PERPETUAL"
    LINEAR_PERPETUAL = "LINEAR_PERPETUAL"


@dataclass(frozen=True)
class InstrumentSpecification:
    """Immutable specifications detailing parameters for price, quantity, and risk."""
    contract_size: Decimal
    tick_size: Decimal
    lot_size: Decimal
    min_quantity: Decimal
    max_leverage: int
    funding_interval_hours: int
    price_precision: int
    quantity_precision: int

    def __post_init__(self):
        # Validate types and values
        if not isinstance(self.contract_size, Decimal):
            object.__setattr__(self, 'contract_size', Decimal(str(self.contract_size)))
        if not isinstance(self.tick_size, Decimal):
            object.__setattr__(self, 'tick_size', Decimal(str(self.tick_size)))
        if not isinstance(self.lot_size, Decimal):
            object.__setattr__(self, 'lot_size', Decimal(str(self.lot_size)))
        if not isinstance(self.min_quantity, Decimal):
            object.__setattr__(self, 'min_quantity', Decimal(str(self.min_quantity)))

        if self.contract_size <= 0:
            raise ValueError(f"Contract size must be strictly positive: {self.contract_size}")
        if self.tick_size <= 0:
            raise ValueError(f"Tick size must be strictly positive: {self.tick_size}")
        if self.lot_size <= 0:
            raise ValueError(f"Lot size must be strictly positive: {self.lot_size}")
        if self.min_quantity < 0:
            raise ValueError(f"Min quantity cannot be negative: {self.min_quantity}")
        if self.max_leverage <= 0:
            raise ValueError(f"Max leverage must be positive: {self.max_leverage}")
        if self.funding_interval_hours < 0:
            raise ValueError(f"Funding interval cannot be negative: {self.funding_interval_hours}")
        if self.price_precision < 0:
            raise ValueError(f"Price precision cannot be negative: {self.price_precision}")
        if self.quantity_precision < 0:
            raise ValueError(f"Quantity precision cannot be negative: {self.quantity_precision}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "contract_size": str(self.contract_size),
            "tick_size": str(self.tick_size),
            "lot_size": str(self.lot_size),
            "min_quantity": str(self.min_quantity),
            "max_leverage": self.max_leverage,
            "funding_interval_hours": self.funding_interval_hours,
            "price_precision": self.price_precision,
            "quantity_precision": self.quantity_precision
        }
