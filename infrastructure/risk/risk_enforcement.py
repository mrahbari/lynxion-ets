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


import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, Tuple

COOLDOWN_JOURNAL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sl_cooldown_journal.json")


class RiskEnforcement:
    """Order-path adapter over EnterpriseRiskManager (enforce + exposure feedback + state)."""

    def __init__(self, risk_manager):
        self._rm = risk_manager
        self._lock = threading.Lock()
        self.checks = 0
        self.denials = 0
        self._sl_cooldowns: Dict[str, float] = self._load_cooldown_journal()

    def _load_cooldown_journal(self) -> Dict[str, float]:
        """Load persistent Stop Loss cooldown timestamps from disk with corruption recovery."""
        try:
            os.makedirs(os.path.dirname(COOLDOWN_JOURNAL_PATH), exist_ok=True)
            if os.path.exists(COOLDOWN_JOURNAL_PATH):
                with open(COOLDOWN_JOURNAL_PATH, "r") as f:
                    return json.load(f)
        except Exception as e:
            from shared.logger import logger
            logger.error(f"⚠️ Cooldown Journal corrupt or unreadable: {e}. Backing up corrupt file and resetting.")
            try:
                if os.path.exists(COOLDOWN_JOURNAL_PATH):
                    os.rename(COOLDOWN_JOURNAL_PATH, f"{COOLDOWN_JOURNAL_PATH}.corrupt.{int(datetime.now().timestamp())}")
            except Exception:
                pass
        return {}

    def _save_cooldown_journal(self) -> None:
        """Save persistent Stop Loss cooldown timestamps atomically via temp file replace."""
        try:
            os.makedirs(os.path.dirname(COOLDOWN_JOURNAL_PATH), exist_ok=True)
            tmp_path = f"{COOLDOWN_JOURNAL_PATH}.tmp.{os.getpid()}"
            with open(tmp_path, "w") as f:
                json.dump(self._sl_cooldowns, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, COOLDOWN_JOURNAL_PATH)
        except Exception as e:
            from shared.logger import logger
            logger.error(f"⚠️ Failed atomic save of Cooldown Journal: {e}")

    def record_stop_loss_exit(self, symbol: str, exit_time: datetime = None) -> None:
        """Record Stop Loss exit for a symbol to activate persistent 60m cooldown across the entire order path."""
        with self._lock:
            ts = (exit_time or datetime.now()).timestamp()
            sym_raw = str(symbol).upper()
            sym_clean = sym_raw.replace("-", "").replace("/", "").replace("_", "")
            self._sl_cooldowns[sym_raw] = ts
            self._sl_cooldowns[sym_clean] = ts
            self._save_cooldown_journal()
            from shared.logger import logger
            logger.info(f"🛑 RISK ENFORCEMENT: Activated 60m Stop Loss Cooldown for {symbol} ({sym_clean})")

    @staticmethod
    def _symbol(order) -> str:
        s = getattr(order, "symbol", None)
        return getattr(s, "value", None) or (str(s) if s is not None else "")

    @staticmethod
    def _price(order) -> float:
        p = getattr(order, "price", None)
        return float(p.amount) if p is not None and getattr(p, "amount", None) is not None else 0.0

    @staticmethod
    def _extract_sl_price(order) -> Optional[float]:
        """Extract stop loss price from order or parent execution intent."""
        # 1. Check order.stop_loss_price
        sl = getattr(order, "stop_loss_price", None)
        if sl is not None and getattr(sl, "amount", None) is not None:
            return float(sl.amount)
        if isinstance(sl, (int, float)) and sl > 0:
            return float(sl)

        # 2. Check order.stop_price
        sp = getattr(order, "stop_price", None)
        if sp is not None and getattr(sp, "amount", None) is not None:
            return float(sp.amount)
        if isinstance(sp, (int, float)) and sp > 0:
            return float(sp)

        # 3. Check order.risk_parameters
        rp = getattr(order, "risk_parameters", None) or {}
        if isinstance(rp, dict):
            for key in ("stop_loss", "sl", "stop_loss_price"):
                val = rp.get(key)
                if val is not None:
                    try:
                        fval = float(val.amount) if hasattr(val, "amount") else float(val)
                        if fval > 0:
                            return fval
                    except (ValueError, TypeError):
                        pass

        # 4. Check parent_execution_intent.risk_parameters
        intent = getattr(order, "parent_execution_intent", None)
        if intent is not None:
            irp = getattr(intent, "risk_parameters", None) or {}
            if isinstance(irp, dict):
                for key in ("stop_loss", "sl", "stop_loss_price"):
                    val = irp.get(key)
                    if val is not None:
                        try:
                            fval = float(val.amount) if hasattr(val, "amount") else float(val)
                            if fval > 0:
                                return fval
                        except (ValueError, TypeError):
                            pass

        return None

    def enforce(self, order) -> tuple[bool, str]:
        """Primary Risk Gate: Validates trading status, position limits, mandatory SL, and SL distance boundaries."""
        with self._lock:
            self.checks += 1
            try:
                if not self._rm.is_trading_allowed():
                    self.denials += 1
                    v = self._rm.get_violations()
                    return False, f"risk engine: trading not allowed ({v[-1] if v else 'limit breached'})"
                symbol = self._symbol(order)
                entry = self._price(order)
                size = float(getattr(order, "quantity", 0) or 0)
                if size <= 0 or entry <= 0:
                    self.denials += 1
                    return False, "risk engine: non-positive size/price"

                # Mandatory Stop-Loss Validation
                sl_price = self._extract_sl_price(order)
                import math
                if sl_price is None or sl_price <= 0 or not math.isfinite(sl_price):
                    self.denials += 1
                    from shared.logger import logger
                    logger.error(
                        f"🛑 MANDATORY RISK GATE REJECTION: Missing Stop-Loss Parameter!\n"
                        f"• Symbol: {symbol}\n"
                        f"• Order Type: {getattr(order, 'order_type', 'UNKNOWN')}\n"
                        f"• Rejection Reason: Every order must contain a valid, finite Stop-Loss price > 0."
                    )
                    return False, f"risk engine: Mandatory Stop-Loss policy violation — order on {symbol} rejected (missing SL)"

                # Side Validation for Stop-Loss (BUY SL < Entry; SELL SL > Entry)
                side_attr = getattr(order, "side", None)
                side_str = getattr(side_attr, "name", str(side_attr)) if side_attr else ""
                side_upper = side_str.upper()

                if entry > 0:
                    if ("BUY" in side_upper or "LONG" in side_upper) and sl_price >= entry:
                        self.denials += 1
                        return False, f"risk engine: Stop-Loss price ({sl_price}) for BUY must be strictly below entry price ({entry})"

                    if ("SELL" in side_upper or "SHORT" in side_upper) and sl_price <= entry:
                        self.denials += 1
                        return False, f"risk engine: Stop-Loss price ({sl_price}) for SELL must be strictly above entry price ({entry})"

                    # Minimum & Maximum Distance Boundaries: 0.1% <= SL distance <= 50%
                    sl_distance_pct = abs(entry - sl_price) / entry
                    if sl_distance_pct < 0.001:
                        self.denials += 1
                        return False, f"risk engine: Stop-Loss distance ({sl_distance_pct * 100:.3f}%) below minimum safety boundary (0.1%)"

                    if sl_distance_pct > 0.50:
                        self.denials += 1
                        return False, f"risk engine: Stop-Loss distance ({sl_distance_pct * 100:.1f}%) exceeds safety boundary (50%)"

                    # 60-Minute Stop Loss Cooldown Hard Gate
                    sym_raw = symbol.upper()
                    sym_clean = sym_raw.replace("-", "").replace("/", "").replace("_", "")
                    now_ts = datetime.now().timestamp()
                    for sym_key in (sym_raw, sym_clean):
                        last_sl_ts = self._sl_cooldowns.get(sym_key)
                        if last_sl_ts and (now_ts - last_sl_ts) < 3600:
                            rem_min = (3600 - (now_ts - last_sl_ts)) / 60.0
                            self.denials += 1
                            from shared.logger import logger
                            logger.warning(
                                f"🛑 HARD RISK GATE DENIAL: 60m Stop Loss Cooldown ACTIVE on {symbol} ({sym_key}) | "
                                f"Remaining = {rem_min:.1f} min"
                            )
                            return False, f"risk engine: 60m Stop Loss Cooldown ACTIVE for {symbol} ({rem_min:.1f}m remaining)"

                    # Sizing boundary enforcement: cap quantity if it exceeds max position limit slightly (<= 5% overflow)
                    max_exposure = getattr(self._rm, 'max_position_exposure', 50000.0)
                    if size * entry > max_exposure:
                        if size * entry <= max_exposure * 1.05:
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
                                size = float(order.quantity)
                        else:
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
