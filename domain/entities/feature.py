from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any
from domain.value_objects import Symbol, ExchangeTimestamp


@dataclass(frozen=True)
class FeatureSnapshot:
    """Canonical representation of calculated Next Generation Liquidity Sweep (NGLS) features."""
    symbol: Symbol
    timestamp: ExchangeTimestamp

    # 1. Order Book Imbalance (OBI)
    obi_ratio: Decimal          # Imbalance at best bid/ask
    obi_multi_level: Decimal    # Imbalance across top 5 levels
    obi_velocity: Decimal       # Rate of change of imbalance

    # 2. Trade Flow Delta
    buy_volume: Decimal         # Aggressive buy volume in window
    sell_volume: Decimal        # Aggressive sell volume in window
    delta: Decimal              # Net volume delta (buy - sell)
    cumulative_delta: Decimal   # Cumulative Volume Delta (CVD)

    # 3. Liquidity Sweep Detection
    is_sweep: bool
    sweep_level_price: Optional[Decimal]
    sweep_volume_consumed: Decimal
    sweep_rejection_ratio: Decimal

    # 4. Absorption Detection
    is_absorption: bool
    absorption_volume: Decimal
    absorption_price_range: Decimal

    # 5. Market Context
    volatility: Decimal         # Rolling standard deviation of price
    spread: Decimal             # Current bid-ask spread
    depth_total: Decimal        # Total volume on book (top 10 levels)
    regime_context: str         # "HIGH_VOLATILITY", "TRENDING", or "RANGING"

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic dictionary serialization."""
        return {
            "symbol": self.symbol.value,
            "timestamp": self.timestamp.to_millis(),
            "obi_ratio": str(self.obi_ratio),
            "obi_multi_level": str(self.obi_multi_level),
            "obi_velocity": str(self.obi_velocity),
            "buy_volume": str(self.buy_volume),
            "sell_volume": str(self.sell_volume),
            "delta": str(self.delta),
            "cumulative_delta": str(self.cumulative_delta),
            "is_sweep": self.is_sweep,
            "sweep_level_price": str(self.sweep_level_price) if self.sweep_level_price is not None else None,
            "sweep_volume_consumed": str(self.sweep_volume_consumed),
            "sweep_rejection_ratio": str(self.sweep_rejection_ratio),
            "is_absorption": self.is_absorption,
            "absorption_volume": str(self.absorption_volume),
            "absorption_price_range": str(self.absorption_price_range),
            "volatility": str(self.volatility),
            "spread": str(self.spread),
            "depth_total": str(self.depth_total),
            "regime_context": self.regime_context
        }
