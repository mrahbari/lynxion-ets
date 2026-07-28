from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any

from domain.value_objects import (
    Symbol,
    ExchangeVenue,
    MarketType,
    ContractType,
    InstrumentSpecification,
)


@dataclass(frozen=True)
class CanonicalInstrument:
    """Canonical representation of an instrument on a specific venue."""
    symbol: Symbol
    base_asset: str
    quote_asset: str
    venue: ExchangeVenue
    market_type: MarketType
    contract_type: ContractType
    specification: InstrumentSpecification

    def __post_init__(self):
        # Enforce validation
        if not self.base_asset or not self.base_asset.strip():
            raise ValueError("Base asset cannot be empty")
        if not self.quote_asset or not self.quote_asset.strip():
            raise ValueError("Quote asset cannot be empty")

        # Symbol consistency check
        expected_base = self.symbol.base_asset()
        expected_quote = self.symbol.quote_asset()
        # Verify that assets match the Symbol constituents
        if self.base_asset.upper() != expected_base.upper():
            raise ValueError(f"Base asset mismatch: {self.base_asset} != {expected_base}")
        if self.quote_asset.upper() != expected_quote.upper():
            raise ValueError(f"Quote asset mismatch: {self.quote_asset} != {expected_quote}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "symbol": self.symbol.value,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "venue": self.venue.value,
            "market_type": self.market_type.value,
            "contract_type": self.contract_type.value,
            "specification": self.specification.to_dict()
        }


@dataclass(frozen=True)
class SymbolMapping:
    """Translation entry mapping a source venue symbol to an execution venue symbol."""
    source_symbol: str
    source_venue: ExchangeVenue
    execution_symbol: str
    execution_venue: ExchangeVenue

    def __post_init__(self):
        if not self.source_symbol.strip():
            raise ValueError("Source symbol cannot be empty")
        if not self.execution_symbol.strip():
            raise ValueError("Execution symbol cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "source_symbol": self.source_symbol,
            "source_venue": self.source_venue.value,
            "execution_symbol": self.execution_symbol,
            "execution_venue": self.execution_venue.value
        }


@dataclass(frozen=True)
class InstrumentMapping:
    """Execution Compatibility mapping translating Alpha Instrument to Execution Instrument."""
    alpha_instrument: CanonicalInstrument
    execution_instrument: CanonicalInstrument
    price_difference: Decimal
    latency_difference_ms: int

    def __post_init__(self):
        if not isinstance(self.price_difference, Decimal):
            object.__setattr__(self, 'price_difference', Decimal(str(self.price_difference)))

        # Sanity check: verify asset pairings match
        if self.alpha_instrument.base_asset != self.execution_instrument.base_asset:
            raise ValueError(f"Base asset mismatch in instrument mapping: {self.alpha_instrument.base_asset} != {self.execution_instrument.base_asset}")
        if self.alpha_instrument.quote_asset != self.execution_instrument.quote_asset:
            raise ValueError(f"Quote asset mismatch in instrument mapping: {self.alpha_instrument.quote_asset} != {self.execution_instrument.quote_asset}")

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization."""
        return {
            "alpha_instrument": self.alpha_instrument.to_dict(),
            "execution_instrument": self.execution_instrument.to_dict(),
            "price_difference": str(self.price_difference),
            "latency_difference_ms": self.latency_difference_ms
        }
