"""
Shared pending orders tracker to ensure consistent duplicate prevention
across all broker services in the system.
"""
import threading
from typing import Dict, List, Tuple
from domain.value_objects import Symbol


class PendingOrdersTracker:
    """
    Singleton class to track pending orders across all broker services
    to prevent duplicate same-direction trades per symbol.
    """
    _instance = None
    _lock = threading.Lock()
    
    # Class-level storage for pending orders to prevent duplicate same-direction trades
    _pending_orders: Dict[str, List[Tuple[str, str]]] = {}
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
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str not in cls._pending_orders:
                cls._pending_orders[symbol_str] = []
            cls._pending_orders[symbol_str].append((side, order_id))

    @classmethod
    def remove_pending_order(cls, symbol: Symbol, order_id: str):
        """Remove an order from the pending orders tracking."""
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str in cls._pending_orders:
                # Remove the specific order ID
                cls._pending_orders[symbol_str] = [
                    (side, oid) for side, oid in cls._pending_orders[symbol_str]
                    if oid != order_id
                ]
                # Clean up empty lists
                if not cls._pending_orders[symbol_str]:
                    del cls._pending_orders[symbol_str]

    @classmethod
    def has_pending_order_in_direction(cls, symbol: Symbol, side: str) -> bool:
        """Check if there's a pending order in the same direction for the symbol."""
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str in cls._pending_orders:
                for pending_side, _ in cls._pending_orders[symbol_str]:
                    if pending_side == side:
                        return True
            return False

    @classmethod
    def get_pending_orders_for_symbol(cls, symbol: Symbol) -> List[Tuple[str, str]]:
        """Get all pending orders for a specific symbol."""
        with cls._pending_orders_instance_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            return cls._pending_orders.get(symbol_str, [])

    @classmethod
    def clear_all_pending_orders(cls):
        """Clear all pending orders (useful for testing or reset)."""
        with cls._pending_orders_instance_lock:
            cls._pending_orders.clear()