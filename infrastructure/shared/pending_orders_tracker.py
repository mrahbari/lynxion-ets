"""
Shared pending orders tracker to ensure consistent duplicate prevention
across all broker services in the system.
"""
import threading
from typing import Dict, List, Tuple
from domain.value_objects import Symbol
from datetime import datetime, timedelta


class PendingOrderInfo:
    """Class to hold information about pending orders"""
    def __init__(self, side: str, order_id: str, timestamp: datetime = None):
        self.side = side
        self.order_id = order_id
        self.timestamp = timestamp or datetime.now()


class PendingOrdersTracker:
    """
    Singleton class to track pending orders across all broker services
    to prevent duplicate same-direction trades per symbol.
    """
    _instance = None
    _lock = threading.Lock()

    # Class-level storage for pending orders to prevent duplicate same-direction trades
    _pending_orders: Dict[str, List[PendingOrderInfo]] = {}
    _pending_orders_instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def add_pending_order(cls, symbol: Symbol, side: str, order_id: str):
        """Add an order to the pending orders tracking."""
        cls.cleanup_old_pending_orders(max_age_seconds=30)
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str not in cls._pending_orders:
                cls._pending_orders[symbol_str] = []
            # Only add if the order_id doesn't already exist
            existing_order_ids = [order_info.order_id for order_info in cls._pending_orders[symbol_str]]
            if order_id not in existing_order_ids:
                cls._pending_orders[symbol_str].append(PendingOrderInfo(side, order_id))

    @classmethod
    def remove_pending_order(cls, symbol: Symbol, order_id: str):
        """Remove an order from the pending orders tracking."""
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str in cls._pending_orders:
                # Remove the specific order ID
                cls._pending_orders[symbol_str] = [
                    order_info for order_info in cls._pending_orders[symbol_str]
                    if order_info.order_id != order_id
                ]
                # Clean up empty lists
                if not cls._pending_orders[symbol_str]:
                    del cls._pending_orders[symbol_str]

    @classmethod
    def has_pending_order_in_direction(cls, symbol: Symbol, side: str) -> bool:
        """Check if there's a pending order in the same direction for the symbol."""
        cls.cleanup_old_pending_orders(max_age_seconds=30)
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str in cls._pending_orders:
                for order_info in cls._pending_orders[symbol_str]:
                    if str(order_info.side).upper() == str(side).upper():
                        return True
            return False

    @classmethod
    def get_pending_orders_for_symbol(cls, symbol: Symbol) -> List[PendingOrderInfo]:
        """Get all pending orders for a specific symbol."""
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            return cls._pending_orders.get(symbol_str, [])

    @classmethod
    def clear_all_pending_orders(cls):
        """Clear all pending orders (useful for testing or reset)."""
        with cls._pending_orders_instance_lock:
            cls._pending_orders.clear()

    @classmethod
    def cleanup_old_pending_orders(cls, max_age_minutes: float = 0.5, max_age_seconds: float = None):
        """Clean up pending orders older than max_age_seconds (or max_age_minutes) to prevent stale entries."""
        import logging
        logger = logging.getLogger("PendingOrdersTracker")

        if max_age_seconds is not None:
            effective_seconds = max_age_seconds
        else:
            effective_seconds = max_age_minutes * 60.0

        with cls._pending_orders_instance_lock:
            current_time = datetime.now()
            removed_count = 0

            for symbol_str, orders_list in list(cls._pending_orders.items()):
                # Filter out orders that are too old
                cutoff_time = current_time - timedelta(seconds=effective_seconds)
                new_orders_list = [
                    order_info for order_info in orders_list
                    if order_info.timestamp > cutoff_time
                ]

                if len(new_orders_list) != len(orders_list):
                    removed_count += len(orders_list) - len(new_orders_list)
                    if new_orders_list:
                        cls._pending_orders[symbol_str] = new_orders_list
                    else:
                        del cls._pending_orders[symbol_str]

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} stale pending orders")