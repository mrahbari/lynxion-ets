"""Shared pending-order semantics with an explicitly scoped state option."""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List

from domain.value_objects import Symbol
from infrastructure.messaging.clock import LiveClock


class PendingOrderInfo:
    """Class to hold information about pending orders."""

    def __init__(self, side: str, order_id: str, timestamp: datetime = None):
        self.side = side
        self.order_id = order_id
        self.timestamp = timestamp or datetime.now()


class PendingOrdersState:
    """The same pending-order rules, with lifetime owned by the caller."""

    def __init__(self, clock=None):
        self._clock = clock if clock is not None else LiveClock()
        self._pending_orders: Dict[str, List[PendingOrderInfo]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _symbol(symbol: Symbol) -> str:
        return symbol.value if hasattr(symbol, "value") else str(symbol)

    def add_pending_order(self, symbol: Symbol, side: str, order_id: str):
        self.cleanup_old_pending_orders(max_age_seconds=30)
        with self._lock:
            symbol_str = self._symbol(symbol)
            if symbol_str not in self._pending_orders:
                self._pending_orders[symbol_str] = []
            if order_id not in [info.order_id for info in self._pending_orders[symbol_str]]:
                self._pending_orders[symbol_str].append(
                    PendingOrderInfo(side, order_id, timestamp=self._clock.now())
                )

    def remove_pending_order(self, symbol: Symbol, order_id: str):
        with self._lock:
            symbol_str = self._symbol(symbol)
            if symbol_str in self._pending_orders:
                self._pending_orders[symbol_str] = [
                    info for info in self._pending_orders[symbol_str]
                    if info.order_id != order_id
                ]
                if not self._pending_orders[symbol_str]:
                    del self._pending_orders[symbol_str]

    def has_pending_order_in_direction(self, symbol: Symbol, side: str) -> bool:
        self.cleanup_old_pending_orders(max_age_seconds=30)
        with self._lock:
            for info in self._pending_orders.get(self._symbol(symbol), []):
                if str(info.side).upper() == str(side).upper():
                    return True
            return False

    def get_pending_orders_for_symbol(self, symbol: Symbol) -> List[PendingOrderInfo]:
        with self._lock:
            return self._pending_orders.get(self._symbol(symbol), [])

    def clear_all_pending_orders(self):
        with self._lock:
            self._pending_orders.clear()

    def cleanup_old_pending_orders(self, max_age_minutes: float = 0.5, max_age_seconds: float = None):
        effective_seconds = max_age_seconds if max_age_seconds is not None else max_age_minutes * 60.0
        with self._lock:
            cutoff_time = self._clock.now() - timedelta(seconds=effective_seconds)
            removed_count = 0
            for symbol_str, orders_list in list(self._pending_orders.items()):
                retained = [info for info in orders_list if info.timestamp > cutoff_time]
                removed_count += len(orders_list) - len(retained)
                if retained:
                    self._pending_orders[symbol_str] = retained
                else:
                    del self._pending_orders[symbol_str]
            if removed_count:
                logging.getLogger("PendingOrdersTracker").info(
                    "Cleaned up %s stale pending orders", removed_count
                )


class PendingOrdersTracker:
    """Backward-compatible process-wide live facade over the shared rules."""

    _instance = None
    _lock = threading.Lock()
    _live_state = PendingOrdersState()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def add_pending_order(cls, symbol: Symbol, side: str, order_id: str):
        cls._live_state.add_pending_order(symbol, side, order_id)

    @classmethod
    def remove_pending_order(cls, symbol: Symbol, order_id: str):
        cls._live_state.remove_pending_order(symbol, order_id)

    @classmethod
    def has_pending_order_in_direction(cls, symbol: Symbol, side: str) -> bool:
        return cls._live_state.has_pending_order_in_direction(symbol, side)

    @classmethod
    def get_pending_orders_for_symbol(cls, symbol: Symbol) -> List[PendingOrderInfo]:
        return cls._live_state.get_pending_orders_for_symbol(symbol)

    @classmethod
    def clear_all_pending_orders(cls):
        cls._live_state.clear_all_pending_orders()

    @classmethod
    def cleanup_old_pending_orders(cls, max_age_minutes: float = 0.5, max_age_seconds: float = None):
        cls._live_state.cleanup_old_pending_orders(max_age_minutes, max_age_seconds)
