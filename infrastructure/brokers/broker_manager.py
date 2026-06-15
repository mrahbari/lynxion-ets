from typing import Dict, List, Optional
from domain.entities import Order
from domain.ports.broker_ports import BrokerPort
from domain.value_objects import Symbol
from domain.entities import Position

class BrokerManager(BrokerPort):
    def __init__(self, brokers: Dict[str, BrokerPort], broker_mapping: Dict[str, str]):
        self.brokers = brokers
        self.broker_mapping = broker_mapping

    def get_broker(self, instrument_type: str) -> BrokerPort:
        broker_name = self.broker_mapping.get(instrument_type)
        if not broker_name:
            raise ValueError(f"No broker configured for instrument type: {instrument_type}")
        broker = self.brokers.get(broker_name)
        if not broker:
            raise ValueError(f"Broker '{broker_name}' not found.")
        if not broker.connected:
            broker.connect()
        return broker

    def get_broker_by_name(self, broker_name: str) -> BrokerPort:
        """Get a specific broker by name directly"""
        broker = self.brokers.get(broker_name)
        if not broker:
            raise ValueError(f"Broker '{broker_name}' not found.")
        if not broker.connected:
            broker.connect()
        return broker

    def place_order(self, order: Order, instrument_type: str) -> str:
        broker = self.get_broker(instrument_type)
        return broker.place_order(order)

    def cancel_order(self, order_id: str, symbol: str, instrument_type: str) -> bool:
        broker = self.get_broker(instrument_type)
        return broker.cancel_order(order_id, symbol)

    def get_order_status(self, order_id: str, symbol: str, instrument_type: str) -> str:
        broker = self.get_broker(instrument_type)
        return broker.get_order_status(order_id, symbol)

    def get_balance(self, asset: str = None, instrument_type: str = 'spot') -> List:
        broker = self.get_broker(instrument_type)
        return broker.get_balance(asset)

    def get_position(self, symbol: Symbol, instrument_type: str = 'futures') -> Optional[Position]:
        broker = self.get_broker(instrument_type)
        return broker.get_position(symbol)

    def get_all_positions(self, instrument_type: str = 'futures') -> List[Position]:
        broker = self.get_broker(instrument_type)
        return broker.get_all_positions()

    def connect(self, instrument_type: str):
        broker = self.get_broker(instrument_type)
        if not broker.connected:
            broker.connect()

    def disconnect(self, instrument_type: str):
        broker = self.get_broker(instrument_type)
        if broker.connected:
            broker.disconnect()
