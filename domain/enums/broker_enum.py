"""
Broker type enumeration for the trading system.
"""
from enum import Enum


class BrokerType(Enum):
    """Enumeration of supported broker types."""
    BINGX = "bingx"
    BINANCE = "binance"
    MEXC = "mexc"
    PHEMEX = "phemex"
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Get list of all supported broker types."""
        return [broker.value for broker in cls]
    
    @classmethod
    def from_string(cls, broker_str: str) -> 'BrokerType':
        """Create BrokerType from string, case-insensitive."""
        broker_str = broker_str.lower()
        for broker in cls:
            if broker.value == broker_str:
                return broker
        raise ValueError(f"Unsupported broker type: {broker_str}. "
                        f"Supported types: {cls.get_supported_types()}")
    
    def get_display_name(self) -> str:
        """Get display name for the broker."""
        display_names = {
            'bingx': 'BingX',
            'binance': 'Binance',
            'mexc': 'MEXC',
            'phemex': 'Phemex'
        }
        return display_names.get(self.value, self.value.title())