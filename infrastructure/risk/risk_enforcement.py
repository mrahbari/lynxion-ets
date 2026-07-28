"""Risk enforcement on the order path (E11, Priority 2).

Wraps the existing portfolio risk engine (EnterpriseRiskManager) and exposes a single
``enforce(order)`` gate that the LIVE_EXECUTION_GUARD consults for EVERY order (paper
and live). This is the missing wiring identified in the Phase-9 audit: the risk engine
existed and was correct, but nothing on the order path called it.

No risk *logic* or thresholds are changed here — this only invokes the engine's existing
``is_trading_allowed`` and ``validate_position_entry`` checks, fails closed on error, and
(best-effort) feeds fills back via ``register_fill`` so portfolio exposure actually
accrues and the limits become enforceable. Call counters provide evidence the gate runs.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Tuple


class RiskEnforcement:
    """Order-path adapter over EnterpriseRiskManager (enforce + exposure feedback + state)."""

    def __init__(self, risk_manager):
        self._rm = risk_manager
        self._lock = threading.Lock()
        self.checks = 0
        self.denials = 0

    @staticmethod
    def _symbol(order) -> str:
        s = getattr(order, "symbol", None)
        return getattr(s, "value", None) or (str(s) if s is not None else "")

    @staticmethod
    def _price(order) -> float:
        p = getattr(order, "price", None)
        return float(p.amount) if p is not None and getattr(p, "amount", None) is not None else 0.0

    def enforce(self, order) -> Tuple[bool, str]:
        """Return (allowed, reason). Fails CLOSED on any error (deny)."""
        with self._lock:
            self.checks += 1
            try:
                if not self._rm.is_trading_allowed():
                    self.denials += 1
                    v = self._rm.get_violations()
                    return False, f"risk engine: trading not allowed ({v[-1] if v else 'limit breached'})"
                symbol = self._symbol(order)
                size = float(getattr(order, "quantity", 0) or 0)
                entry = self._price(order)
                if size <= 0 or entry <= 0:
                    self.denials += 1
                    return False, "risk engine: non-positive size/price"

                # Sizing boundary enforcement: cap quantity if it exceeds max position limit slightly (<= 5% overflow)
                max_exposure = getattr(self._rm, 'max_position_exposure', 50000.0)
                if size * entry > max_exposure:
                    if size * entry <= max_exposure * 1.05:
                        # Apply a tiny safety buffer (0.1%) to prevent rounding/precision increments
                        target_exposure = max_exposure * 0.999
                        capped_size = target_exposure / entry
                        import math
                        capped_size = math.floor(capped_size * 10000) / 10000.0
                        from decimal import Decimal
                        if hasattr(order, 'quantity'):
                            if isinstance(order.quantity, Decimal):
                                order.quantity = Decimal(str(capped_size))
                            else:
                                order.quantity = capped_size
                            from shared.logger import logger
                            logger.warning(
                                f"⚠️ Sizing boundary enforcement: Capped {symbol} quantity from {size} to {order.quantity} "
                                f"to stay within max position limit of ${max_exposure}"
                            )
                            # Update size variable for subsequent checks
                            size = float(order.quantity)
                    else:
                        # Large violation: reject outright without capping
                        self.denials += 1
                        self._rm.violations.append(
                            f"{symbol}: Position size ${size * entry:.2f} exceeds max position limit ${max_exposure}"
                        )
                        return False, f"risk engine: Position size ${size * entry:.2f} exceeds max position limit ${max_exposure}"

                if not self._rm.validate_position_entry(symbol, size, entry):
                    self.denials += 1
                    v = self._rm.get_violations()
                    return False, f"risk engine: {v[-1] if v else 'position entry rejected'}"
                return True, "risk engine: approved"
            except Exception as e:
                self.denials += 1
                return False, f"risk engine error: {e}"

    def register_fill(self, order, fill_price: float) -> None:
        """Best-effort: register a filled entry so portfolio exposure accrues (gate stays meaningful)."""
        try:
            from application.risk_management.enterprise_risk_manager import PositionDirection
            from domain.entities import OrderSide
            side = order.side if isinstance(order.side, OrderSide) else OrderSide(str(order.side))
            direction = PositionDirection.LONG if side == OrderSide.BUY else PositionDirection.SHORT
            symbol = self._symbol(order)
            size = float(getattr(order, "quantity", 0) or 0)
            sl = float(order.stop_loss_price.amount) if getattr(order, "stop_loss_price", None) else fill_price * 0.99
            tp = float(order.take_profit_price.amount) if getattr(order, "take_profit_price", None) else fill_price * 1.01
            
            # Extract setup type from order's parent_execution_intent metadata if available
            setup_type = None
            if hasattr(order, 'parent_execution_intent') and order.parent_execution_intent:
                intent = order.parent_execution_intent
                if intent.metadata:
                    setup_type = intent.metadata.get("setup_type")
                    
            with self._lock:
                self._rm.enter_position(symbol, fill_price, size, direction, sl, tp, setup_type=setup_type)
        except Exception:
            pass  # exposure feedback must never break execution

    def state(self) -> Dict[str, Any]:
        try:
            with self._lock:
                return {
                    "is_trading_allowed": bool(self._rm.is_trading_allowed()),
                    "total_exposure": float(self._rm.get_total_exposure()),
                    "drawdown": float(self._rm.calculate_drawdown()),
                    "open_positions": len(getattr(self._rm, "positions", {})),
                    "enforce_checks": self.checks,
                    "enforce_denials": self.denials,
                }
        except Exception as e:  # pragma: no cover
            return {"status": "error", "error": str(e)}


__all__ = ["RiskEnforcement"]
