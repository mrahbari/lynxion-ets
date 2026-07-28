"""1m Execution Optimizer enforcing maker-limit orders, spread gating, and TIF settings."""

from typing import Dict, Any, Optional
from decimal import Decimal
from domain.value_objects import Symbol


class ExecutionOptimizer:
    """
    1m Execution Optimizer.
    Determines optimal execution prices (maker-first), spread validation, and TIF enforcements.
    """

    def __init__(self, max_spread_pct: float = 0.001):
        self.max_spread_pct = max_spread_pct

    def optimize_order(self, symbol: Symbol, direction: str, current_price: float,
                       best_bid: float, best_ask: float, quantity: float) -> Optional[Dict[str, Any]]:
        """
        Validate spread and generate optimized maker limit order parameters.
        """
        spread = best_ask - best_bid
        if current_price > 0:
            spread_pct = spread / current_price
            if spread_pct > self.max_spread_pct:
                # Spread validation failed (spread too wide)
                return None

        # Determine limit price based on direction (maker-first)
        limit_price = best_bid if direction == "BUY" else best_ask

        return {
            "symbol": symbol.value if hasattr(symbol, "value") else str(symbol),
            "order_side": direction,
            "order_type": "LIMIT",
            "price": Decimal(str(limit_price)),
            "quantity": Decimal(str(quantity)),
            "time_in_force": "POST_ONLY"  # Enforces maker execution
        }
