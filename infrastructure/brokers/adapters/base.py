from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from shared.types import Order, Fill, Balance, Position


class BrokerInterface(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        pass

    @abstractmethod
    def get_balance(self, asset: str = None) -> Optional[Balance]:
        pass

    @abstractmethod
    def get_all_balances(self) -> List[Balance]:
        pass

    @abstractmethod
    def place_order(self, order: Order) -> Optional[str]:
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str = None) -> List[Order]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        pass

    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str = None) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        pass

    @abstractmethod
    def get_price(self, symbol: str) -> Optional[float]:
        pass

    @abstractmethod
    def get_orderbook(self, symbol: str, depth: int = 10) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_klines(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        pass
