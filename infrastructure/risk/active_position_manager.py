"""Production Active Position Trailing Stop & Breakeven Protection Engine.

Provides real-time dynamic position management across all active positions:
1. Breakeven Protection: When ROE >= +5.0% (+0.5% price gain at 10x leverage),
   moves Stop Loss to entry_price +/- 0.1% fee buffer, guaranteeing the trade cannot turn negative.
2. Dynamic Trailing Stop: When ROE >= +10.0% (+1.0% price gain at 10x leverage),
   continuously trails the Stop Loss 0.5% behind the peak high-water mark price, locking in gains.
3. Clean Full-Position Exits: Eliminates flawed partial closing friction, ensuring high-expectancy
   clean exits at profit without orphan slices or minimum lot-size rejections.
4. Universal & Dynamic: Zero hardcoded symbols; applies dynamically to all perpetual assets.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from shared.logger import logger


class ActivePositionManager:
    """Thread-safe real-time manager for Trailing Stops, Breakeven Protection, and Profit Locking."""

    _instance: Optional[ActivePositionManager] = None
    _lock = threading.RLock()

    def __init__(
        self,
        be_trigger_roe: float = 6.0,        # +6.0% ROE to trigger Breakeven (+0.6% price move @ 10x)
        trail_trigger_roe: float = 10.0,    # +10.0% ROE to activate Trailing Stop (+1.0% price move @ 10x)
        trail_distance_pct: float = 0.005,  # 0.5% trailing distance from peak price
        fee_buffer_pct: float = 0.0035,     # 0.35% price buffer (3.5% ROE @ 10x) to strictly cover taker fees + spread + slippage
        leverage_multiplier: float = 10.0   # Default leverage calculation factor
    ):
        self.be_trigger_roe = be_trigger_roe
        self.trail_trigger_roe = trail_trigger_roe
        self.trail_distance_pct = trail_distance_pct
        self.fee_buffer_pct = fee_buffer_pct
        self.leverage_multiplier = leverage_multiplier

        # symbol -> position tracking state
        self._positions_state: Dict[str, Dict[str, Any]] = {}
        self._last_eval_time: float = 0.0

    @classmethod
    def get_instance(cls) -> ActivePositionManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def normalize_symbol(sym: Any) -> str:
        s = getattr(sym, "value", None) or str(sym or "")
        return s.upper().replace("-", "").replace("/", "").replace("_", "").strip()

    @staticmethod
    def _extract_float(val: Any) -> float:
        """Safely extract float from Money, Decimal, dict, int, str, or float."""
        if val is None:
            return 0.0
        if hasattr(val, "amount"):
            try:
                return float(val.amount)
            except (ValueError, TypeError):
                pass
        if hasattr(val, "value"):
            try:
                return float(val.value)
            except (ValueError, TypeError):
                pass
        if isinstance(val, dict):
            return float(val.get("amount", 0) or val.get("price", 0) or val.get("value", 0) or 0)
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def evaluate_open_positions(self, broker: Any, current_prices: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Evaluate all open positions from the broker and execute Trailing Stop / Breakeven adjustments.

        Returns a list of actions taken (e.g. SL updated, Breakeven triggered, Trailing Exit executed).
        """
        actions_taken = []
        with self._lock:
            try:
                # 1. Fetch live open positions from broker
                positions = []
                if hasattr(broker, "get_all_positions"):
                    positions = broker.get_all_positions() or []
                elif hasattr(broker, "get_positions"):
                    positions = broker.get_positions() or []

                active_open_symbols = set()

                for pos in positions:
                    qty = self._extract_float(
                        getattr(pos, "quantity", 0) or getattr(pos, "position_amt", 0) or (pos.get("positionAmt") if isinstance(pos, dict) else 0)
                    )
                    if abs(qty) <= 0:
                        continue

                    raw_sym = getattr(pos, "symbol", "") or (pos.get("symbol") if isinstance(pos, dict) else "")
                    clean_sym = self.normalize_symbol(raw_sym)
                    active_open_symbols.add(clean_sym)

                    pos_side_raw = (
                        getattr(pos, "side", None)
                        or (pos.get("positionSide") if isinstance(pos, dict) else None)
                        or (pos.get("side") if isinstance(pos, dict) else None)
                        or ""
                    )
                    side_str = getattr(pos_side_raw, "value", str(pos_side_raw)).upper()
                    if "SHORT" in side_str or "SELL" in side_str:
                        is_long = False
                    elif "LONG" in side_str or "BUY" in side_str:
                        is_long = True
                    elif qty < 0:
                        is_long = False
                    else:
                        is_long = True

                    entry_val = getattr(pos, "entry_price", None) or getattr(pos, "avg_price", None) or (pos.get("avgPrice") if isinstance(pos, dict) else 0)
                    entry_price = self._extract_float(entry_val)
                    if entry_price <= 0:
                        continue

                    # Determine current price
                    curr_price = None
                    if current_prices and clean_sym in current_prices:
                        curr_price = float(current_prices[clean_sym])
                    elif hasattr(pos, "mark_price") and self._extract_float(pos.mark_price) > 0:
                        curr_price = self._extract_float(pos.mark_price)
                    elif isinstance(pos, dict) and self._extract_float(pos.get("markPrice") or pos.get("mark_price")) > 0:
                        curr_price = self._extract_float(pos.get("markPrice") or pos.get("mark_price"))
                    elif hasattr(pos, "current_price") and self._extract_float(pos.current_price) > 0:
                        curr_price = self._extract_float(pos.current_price)
                    elif hasattr(broker, "get_current_price"):
                        try:
                            curr_price = float(broker.get_current_price(clean_sym))
                        except Exception:
                            pass

                    # Fallback live price fetch from Binance/exchange if still missing
                    if not curr_price or curr_price <= 0:
                        try:
                            from domain.value_objects import Symbol as DomainSymbol
                            from infrastructure.data.binance_client import BinanceClient
                            b_client = BinanceClient()
                            p = b_client.get_symbol_price(clean_sym)
                            if p and float(p) > 0:
                                curr_price = float(p)
                        except Exception:
                            pass

                    if not curr_price or curr_price <= 0:
                        continue

                    # Initialize state if not tracked
                    if clean_sym not in self._positions_state:
                        self._positions_state[clean_sym] = {
                            "symbol": clean_sym,
                            "is_long": is_long,
                            "entry_price": entry_price,
                            "quantity": abs(qty),
                            "peak_price": curr_price,
                            "peak_roe": 0.0,
                            "breakeven_active": False,
                            "current_sl_price": 0.0,
                            "trailing_sl_price": 0.0,
                            "first_seen": time.time(),
                        }

                    state = self._positions_state[clean_sym]
                    state["entry_price"] = entry_price
                    state["quantity"] = abs(qty)
                    state["is_long"] = is_long

                    # Calculate price PnL % and estimated ROE %
                    if is_long:
                        price_pnl_pct = (curr_price - entry_price) / entry_price
                        state["peak_price"] = max(state.get("peak_price", curr_price), curr_price)
                    else:
                        price_pnl_pct = (entry_price - curr_price) / entry_price
                        state["peak_price"] = min(state.get("peak_price", curr_price), curr_price)

                    roe_pct = price_pnl_pct * self.leverage_multiplier * 100.0
                    state["peak_roe"] = max(state.get("peak_roe", 0.0), roe_pct)
                    peak_p = state["peak_price"]

                    # --- STAGE 0: VERIFY / ATTACH INITIAL PROTECTIVE STOP LOSS ON BROKER ---
                    if not state.get("initial_sl_verified", False):
                        state["initial_sl_verified"] = True
                        target_broker = self._resolve_target_broker(broker, clean_sym)
                        if hasattr(target_broker, "get_pending_orders"):
                            try:
                                from infrastructure.utils.symbol_format_helper import SymbolFormatHelper
                                formatted_sym = SymbolFormatHelper.format_symbol_for_exchange(clean_sym, "bingx")
                                pending = target_broker.get_pending_orders(formatted_sym) or []
                                stop_orders = [
                                    order for order in pending
                                    if "STOP" in str(order.get("type", "")).upper()
                                    and str(order.get("side", "")).upper() == ("SELL" if is_long else "BUY")
                                    and str(order.get("positionSide", "")).upper() == ("LONG" if is_long else "SHORT")
                                ]
                                has_sl = bool(stop_orders)
                                if has_sl:
                                    # Exchange state is the restart-safe source of truth.  Hydrate
                                    # it before evaluating a new candidate so a process restart does
                                    # not blindly amend an already protected position.
                                    existing_sl = self._extract_float(
                                        stop_orders[0].get("stopPrice", stop_orders[0].get("stop_price"))
                                    )
                                    if existing_sl > 0:
                                        state["current_sl_price"] = existing_sl
                                        locked_at_breakeven = (
                                            existing_sl >= entry_price * (1.0 + self.fee_buffer_pct)
                                            if is_long else
                                            existing_sl <= entry_price * (1.0 - self.fee_buffer_pct)
                                        )
                                        if locked_at_breakeven:
                                            state["breakeven_active"] = True
                                            state["trailing_sl_price"] = existing_sl
                                if not has_sl and not state.get("breakeven_active", False) and state.get("current_sl_price", 0.0) == 0.0:
                                    default_sl_pct = 0.03  # 3% protective initial stop loss
                                    if is_long:
                                        init_sl = min(entry_price * (1.0 - default_sl_pct), curr_price * 0.99)
                                    else:
                                        init_sl = max(entry_price * (1.0 + default_sl_pct), curr_price * 1.01)
                                    logger.warning(
                                        f"🚨 [ACTIVE POSITION MANAGER] MISSING STOP LOSS DETECTED: {clean_sym} "
                                        f"has no active Stop Loss on exchange! Attaching protective SL at ${init_sl:.4f}"
                                    )
                                    if self._sync_sl_to_exchange(broker, clean_sym, is_long, abs(qty), init_sl):
                                        state["current_sl_price"] = init_sl
                                    else:
                                        state["initial_sl_verified"] = False
                            except Exception as ex:
                                logger.error(f"Error checking/attaching initial SL for {clean_sym}: {ex}")

                    # --- STAGE 1: BREAKEVEN STOP ACTIVATION (+8.0% ROE) ---
                    if roe_pct >= self.be_trigger_roe and not state.get("breakeven_active", False):
                        if is_long:
                            be_sl = entry_price * (1.0 + self.fee_buffer_pct)
                            if be_sl >= curr_price:
                                be_sl = curr_price * 0.998
                        else:
                            be_sl = entry_price * (1.0 - self.fee_buffer_pct)
                            if be_sl <= curr_price:
                                be_sl = curr_price * 1.002

                        if self._sync_sl_to_exchange(broker, clean_sym, is_long, abs(qty), be_sl):
                            state["breakeven_active"] = True
                            state["current_sl_price"] = be_sl
                            state["trailing_sl_price"] = be_sl
                            action = {
                                "type": "BREAKEVEN_ACTIVATED",
                                "symbol": clean_sym,
                                "side": "LONG" if is_long else "SHORT",
                                "entry_price": entry_price,
                                "current_price": curr_price,
                                "roe_pct": roe_pct,
                                "new_sl_price": be_sl,
                            }
                            actions_taken.append(action)
                            logger.warning(
                                f"🛡️ [ACTIVE POSITION MANAGER] BREAKEVEN ACTIVATED: {clean_sym} "
                                f"ROE={roe_pct:+.2f}% >= +{self.be_trigger_roe}%. "
                                f"SL moved to Breakeven+Buffer: ${be_sl:.4f} (Entry: ${entry_price:.4f})"
                            )

                    # --- STAGE 1.5: TIME-DECAY STALE POSITION PROTECTION ---
                    elapsed_hours = (time.time() - state.get("first_seen", time.time())) / 3600.0

                    # 1. Stale in-profit trade (>= 3.0h open & ROE >= +3.5% fee coverage) -> Force Breakeven Lock
                    if elapsed_hours >= 3.0 and roe_pct >= (self.fee_buffer_pct * self.leverage_multiplier * 100.0) and not state.get("breakeven_active", False):
                        if is_long:
                            be_sl = entry_price * (1.0 + self.fee_buffer_pct)
                            if be_sl >= curr_price:
                                be_sl = curr_price * 0.998
                        else:
                            be_sl = entry_price * (1.0 - self.fee_buffer_pct)
                            if be_sl <= curr_price:
                                be_sl = curr_price * 1.002

                        if self._sync_sl_to_exchange(broker, clean_sym, is_long, abs(qty), be_sl):
                            state["breakeven_active"] = True
                            state["current_sl_price"] = be_sl
                            state["trailing_sl_price"] = be_sl
                            action = {
                                "type": "TIME_DECAY_BREAKEVEN_ACTIVATED",
                                "symbol": clean_sym,
                                "side": "LONG" if is_long else "SHORT",
                                "entry_price": entry_price,
                                "current_price": curr_price,
                                "roe_pct": roe_pct,
                                "new_sl_price": be_sl,
                                "elapsed_hours": elapsed_hours
                            }
                            actions_taken.append(action)
                            logger.warning(
                                f"⏳ [ACTIVE POSITION MANAGER] TIME-DECAY BREAKEVEN ACTIVATED: {clean_sym} "
                                f"held for {elapsed_hours:.1f}h with ROE={roe_pct:+.2f}%. "
                                f"SL moved to Breakeven+Buffer: ${be_sl:.4f} (Entry: ${entry_price:.4f})"
                            )

                    # 2. Stale stagnant trade (>= 8.0h open without hitting Breakeven) -> Tighten Stop by 30%
                    elif elapsed_hours >= 8.0 and not state.get("breakeven_active", False) and not state.get("time_decay_tightened", False):
                        state["time_decay_tightened"] = True
                        curr_sl = state.get("current_sl_price", 0.0)
                        if is_long and curr_sl > 0 and curr_sl < entry_price:
                            tightened_sl = entry_price - (entry_price - curr_sl) * 0.70
                            if tightened_sl < curr_price * 0.998:
                                action = {
                                    "type": "TIME_DECAY_STOP_TIGHTENED",
                                    "symbol": clean_sym,
                                    "side": "LONG",
                                    "entry_price": entry_price,
                                    "current_price": curr_price,
                                    "roe_pct": roe_pct,
                                    "new_sl_price": tightened_sl,
                                    "elapsed_hours": elapsed_hours
                                }
                                if self._sync_sl_to_exchange(broker, clean_sym, is_long, abs(qty), tightened_sl):
                                    state["current_sl_price"] = tightened_sl
                                    actions_taken.append(action)
                                    logger.warning(
                                        f"⏳ [ACTIVE POSITION MANAGER] TIME-DECAY SL TIGHTENED: {clean_sym} LONG "
                                        f"held for {elapsed_hours:.1f}h without progress. "
                                        f"SL tightened by 30% to ${tightened_sl:.4f} to cut risk on stagnant trade."
                                    )
                        elif not is_long and curr_sl > 0 and curr_sl > entry_price:
                            tightened_sl = entry_price + (curr_sl - entry_price) * 0.70
                            if tightened_sl > curr_price * 1.002:
                                action = {
                                    "type": "TIME_DECAY_STOP_TIGHTENED",
                                    "symbol": clean_sym,
                                    "side": "SHORT",
                                    "entry_price": entry_price,
                                    "current_price": curr_price,
                                    "roe_pct": roe_pct,
                                    "new_sl_price": tightened_sl,
                                    "elapsed_hours": elapsed_hours
                                }
                                if self._sync_sl_to_exchange(broker, clean_sym, is_long, abs(qty), tightened_sl):
                                    state["current_sl_price"] = tightened_sl
                                    actions_taken.append(action)
                                    logger.warning(
                                        f"⏳ [ACTIVE POSITION MANAGER] TIME-DECAY SL TIGHTENED: {clean_sym} SHORT "
                                        f"held for {elapsed_hours:.1f}h without progress. "
                                        f"SL tightened by 30% to ${tightened_sl:.4f} to cut risk on stagnant trade."
                                    )

                    # --- STAGE 2: DYNAMIC TRAILING STOP RATCHET (+10.0% ROE) ---
                    min_locked_roe = self.fee_buffer_pct * self.leverage_multiplier * 100.0  # +3.5% ROE minimum
                    if roe_pct >= self.trail_trigger_roe:
                        if is_long:
                            candidate_sl = min(peak_p * (1.0 - self.trail_distance_pct), curr_price * 0.997)
                            locked_roe = ((candidate_sl - entry_price) / entry_price) * self.leverage_multiplier * 100.0
                            # Long SL can only increase (monotonic ratchet) and must lock >= min_locked_roe
                            if candidate_sl > state.get("trailing_sl_price", 0.0) and locked_roe >= min_locked_roe:
                                action = {
                                    "type": "TRAILING_STOP_RATCHET",
                                    "symbol": clean_sym,
                                    "side": "LONG",
                                    "entry_price": entry_price,
                                    "peak_price": peak_p,
                                    "current_price": curr_price,
                                    "roe_pct": roe_pct,
                                    "new_sl_price": candidate_sl,
                                    "locked_roe_pct": locked_roe,
                                }
                                if self._sync_sl_to_exchange(broker, clean_sym, is_long, abs(qty), candidate_sl):
                                    state["trailing_sl_price"] = candidate_sl
                                    state["current_sl_price"] = max(state.get("current_sl_price", 0.0), candidate_sl)
                                    actions_taken.append(action)
                                    logger.warning(
                                        f"📈 [ACTIVE POSITION MANAGER] TRAILING STOP RATCHET: {clean_sym} LONG "
                                        f"Peak ROE={state['peak_roe']:+.2f}%, Current ROE={roe_pct:+.2f}%. "
                                        f"SL raised to ${candidate_sl:.4f} (Locked ROE: {locked_roe:+.2f}%)"
                                    )
                        else:
                            candidate_sl = max(peak_p * (1.0 + self.trail_distance_pct), curr_price * 1.003)
                            locked_roe = ((entry_price - candidate_sl) / entry_price) * self.leverage_multiplier * 100.0
                            # Short SL can only decrease (monotonic ratchet) and must lock >= min_locked_roe
                            if (state.get("trailing_sl_price", 0.0) == 0.0 or candidate_sl < state.get("trailing_sl_price", 0.0)) and locked_roe >= min_locked_roe:
                                action = {
                                    "type": "TRAILING_STOP_RATCHET",
                                    "symbol": clean_sym,
                                    "side": "SHORT",
                                    "entry_price": entry_price,
                                    "peak_price": peak_p,
                                    "current_price": curr_price,
                                    "roe_pct": roe_pct,
                                    "new_sl_price": candidate_sl,
                                    "locked_roe_pct": locked_roe,
                                }
                                if self._sync_sl_to_exchange(broker, clean_sym, is_long, abs(qty), candidate_sl):
                                    state["trailing_sl_price"] = candidate_sl
                                    state["current_sl_price"] = min(state.get("current_sl_price", 999999.0), candidate_sl)
                                    actions_taken.append(action)
                                    logger.warning(
                                        f"📉 [ACTIVE POSITION MANAGER] TRAILING STOP RATCHET: {clean_sym} SHORT "
                                        f"Peak ROE={state['peak_roe']:+.2f}%, Current ROE={roe_pct:+.2f}%. "
                                        f"SL lowered to ${candidate_sl:.4f} (Locked ROE: {locked_roe:+.2f}%)"
                                    )

                    # --- STAGE 3: TRAILING STOP HIT ENFORCEMENT ---
                    sl_price = state.get("trailing_sl_price", 0.0)
                    if sl_price > 0:
                        should_exit = False
                        if is_long and curr_price <= sl_price:
                            should_exit = True
                        elif not is_long and curr_price >= sl_price:
                            should_exit = True

                        if should_exit:
                            logger.warning(
                                f"🎯 [ACTIVE POSITION MANAGER] TRAILING STOP BREACHED: {clean_sym} "
                                f"Current Price=${curr_price:.4f} crossed Trailing SL=${sl_price:.4f}. "
                                f"Executing immediate market close to lock in profit!"
                            )
                            self._execute_market_close(broker, clean_sym, is_long, abs(qty))
                            action = {
                                "type": "TRAILING_EXIT_EXECUTED",
                                "symbol": clean_sym,
                                "side": "LONG" if is_long else "SHORT",
                                "exit_price": curr_price,
                                "sl_price": sl_price,
                                "roe_pct": roe_pct,
                            }
                            actions_taken.append(action)

                # Clean up closed positions from memory
                for sym in list(self._positions_state.keys()):
                    if sym not in active_open_symbols:
                        del self._positions_state[sym]

                self._last_eval_time = time.time()
            except Exception as e:
                logger.error(f"Error in ActivePositionManager.evaluate_open_positions: {e}", exc_info=True)

        return actions_taken

    def _resolve_target_broker(self, broker: Any, symbol: Optional[str] = None) -> Any:
        """Resolve the active perpetual broker adapter from composite or multi-broker services."""
        target = broker
        if hasattr(broker, "brokers") and isinstance(broker.brokers, dict):
            target = broker.brokers.get("bingx") or next(iter(broker.brokers.values()), broker)
        if hasattr(target, "broker"):
            target = target.broker
        return target

    def _sync_sl_to_exchange(self, broker: Any, symbol: str, is_long: bool, quantity: float, new_sl_price: float) -> bool:
        """Replace a broker stop and confirm that the requested stop is actually pending.

        State is deliberately not updated by this method's callers until this returns
        true.  A rejected or invisible replacement must be retried on the next loop,
        rather than being reported as protected based on local state alone.
        """
        try:
            target_broker = self._resolve_target_broker(broker)
            close_side = "SELL" if is_long else "BUY"
            pos_side = "LONG" if is_long else "SHORT"
            formatted_qty = str(quantity)

            # Format symbol for exchange (e.g. BTC-USDT for BingX)
            from infrastructure.utils.symbol_format_helper import SymbolFormatHelper
            formatted_symbol = SymbolFormatHelper.format_symbol_for_exchange(symbol, "bingx")

            # The BingX adapter performs its own cancel-and-replace only after the
            # exchange reports a position-stop conflict.  Cancelling here first can
            # leave a live position unprotected if the replacement is rejected.
            max_sl_attempts = 3
            placed = False
            for attempt in range(1, max_sl_attempts + 1):
                try:
                    if hasattr(target_broker, "_place_conditional_order"):
                        res = target_broker._place_conditional_order(
                            symbol=formatted_symbol,
                            side=close_side,
                            quantity=formatted_qty,
                            stop_price=str(new_sl_price),
                            order_type="STOP_MARKET",
                            position_side=pos_side
                        )
                    elif hasattr(target_broker, "_broker") and hasattr(target_broker._broker, "_place_conditional_order"):
                        res = target_broker._broker._place_conditional_order(
                            symbol=formatted_symbol,
                            side=close_side,
                            quantity=formatted_qty,
                            stop_price=str(new_sl_price),
                            order_type="STOP_MARKET",
                            position_side=pos_side
                        )
                    else:
                        res = {"success": False, "error": "No _place_conditional_order method available"}

                    if res.get("success"):
                        placed = self._verify_pending_stop(
                            target_broker, formatted_symbol, close_side, pos_side, new_sl_price
                        )
                        if placed:
                            logger.warning(f"✅ Confirmed Broker Stop Loss on exchange for {symbol}: ${new_sl_price:.4f} (Attempt {attempt})")
                            break
                        logger.warning(f"SL placement for {symbol} was accepted but could not be verified as pending (Attempt {attempt})")
                    else:
                        err_msg = res.get("error", "Unknown error")
                        logger.warning(f"SL placement attempt {attempt}/{max_sl_attempts} failed on {symbol}: {err_msg}")
                        if attempt < max_sl_attempts:
                            time.sleep(0.30)
                except Exception as place_err:
                    logger.warning(f"Error during SL placement attempt {attempt}/{max_sl_attempts} on {symbol}: {place_err}")
                    if attempt < max_sl_attempts:
                        time.sleep(0.30)

            if not placed:
                logger.error(f"❌ Failed to update Broker Stop Loss on exchange for {symbol} after {max_sl_attempts} attempts")
            return placed
        except Exception as e:
            logger.warning(f"Could not sync updated SL order on exchange for {symbol}: {e}")
            return False

    @staticmethod
    def _verify_pending_stop(target_broker: Any, formatted_symbol: str, close_side: str,
                             position_side: str, expected_stop_price: float) -> bool:
        """Return true only when the requested position-closing stop is visible."""
        if not hasattr(target_broker, "get_pending_orders"):
            return False
        for _ in range(3):
            try:
                pending = target_broker.get_pending_orders(formatted_symbol) or []
                for order in pending:
                    if "STOP" not in str(order.get("type", "")).upper():
                        continue
                    if str(order.get("side", "")).upper() != close_side:
                        continue
                    if str(order.get("positionSide", "")).upper() != position_side:
                        continue
                    actual = ActivePositionManager._extract_float(
                        order.get("stopPrice", order.get("stop_price", order.get("triggerPrice")))
                    )
                    tolerance = max(abs(expected_stop_price) * 0.0001, 1e-8)
                    if abs(actual - expected_stop_price) <= tolerance:
                        return True
            except Exception as verify_err:
                logger.warning(f"Could not verify pending stop for {formatted_symbol}: {verify_err}")
            time.sleep(0.2)
        return False

    def _execute_market_close(self, broker: Any, symbol: str, is_long: bool, quantity: float) -> None:
        """Execute a market close order for the position."""
        try:
            target_broker = self._resolve_target_broker(broker)
            close_side = "SELL" if is_long else "BUY"
            pos_side = "LONG" if is_long else "SHORT"

            if hasattr(target_broker, "_unwind_position"):
                target_broker._unwind_position(
                    symbol=symbol,
                    original_side="BUY" if is_long else "SELL",
                    quantity=str(quantity),
                    position_side=pos_side
                )
            elif hasattr(target_broker, "_broker") and hasattr(target_broker._broker, "_unwind_position"):
                from infrastructure.utils.symbol_format_helper import SymbolFormatHelper
                sym_str = SymbolFormatHelper.format_symbol_for_exchange(symbol, "bingx")
                target_broker._broker._unwind_position(
                    symbol=sym_str,
                    original_side="BUY" if is_long else "SELL",
                    quantity=str(quantity),
                    position_side=pos_side
                )
        except Exception as e:
            logger.error(f"Failed to execute trailing exit market close for {symbol}: {e}")


# Canonical singleton instance
active_position_manager = ActivePositionManager.get_instance()
