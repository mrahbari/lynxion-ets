"""
Broker Execution Service - Handles broker configuration and execution logic
This service provides a clean interface for broker execution while keeping
the main runner files clean and focused.
"""
from typing import Dict, Any, Optional
from domain.ports.execution_ports import ExecutionPort
from domain.entities.trading_entities import Order
from domain.value_objects import Symbol
from domain.enums.broker_enum import BrokerType
from shared.logger import EnhancedLogger
import os


class BrokerExecutionService(ExecutionPort):
    """
    A configurable execution service that can work with multiple brokers.
    This service handles broker configuration and execution logic.
    """

    def __init__(self, broker_type: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the broker execution service.

        Args:
            broker_type: Type of broker ('bingx', 'binance', 'mexc', 'phemex').
                        If None, will use DEFAULT_BROKER environment variable.
            config: Optional configuration dictionary. If None, will load from environment.
        """
        from infrastructure.brokers.broker_adapters import (
            BingXBrokerAdapter, BinanceBrokerAdapter, MEXCBrokerAdapter, PhemexBrokerAdapter
        )

        # Determine broker type
        if broker_type is None:
            broker_type_str = os.getenv('DEFAULT_BROKER', 'bingx').lower()
        else:
            broker_type_str = broker_type.lower()

        # Convert to enum
        try:
            self.broker_type_enum = BrokerType.from_string(broker_type_str)
            self.broker_type = self.broker_type_enum.value
        except ValueError:
            raise ValueError(
                f"Unsupported broker type: {broker_type_str}. "
                f"Supported types: {BrokerType.get_supported_types()}"
            )

        # Load configuration
        if config is None:
            config = self._load_config_from_env(self.broker_type)

        self.logger = EnhancedLogger("BrokerExecutionService")

        # Initialize the appropriate broker adapter
        if self.broker_type == BrokerType.BINGX.value:
            self.broker = BingXBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        elif self.broker_type == BrokerType.BINANCE.value:
            self.broker = BinanceBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        elif self.broker_type == BrokerType.MEXC.value:
            self.broker = MEXCBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        elif self.broker_type == BrokerType.PHEMEX.value:
            self.broker = PhemexBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        else:
            raise ValueError(
                f"Unsupported broker type: {self.broker_type}. "
                f"Supported types: {BrokerType.get_supported_types()}"
            )

        # Try to connect the broker during initialization
        try:
            if hasattr(self.broker, 'connect'):
                self.broker.connect()
        except Exception as e:
            self.logger.warning(f"Could not connect broker {self.broker_name} during initialization: {e}")

        # Initialize the appropriate broker adapter
        if self.broker_type == BrokerType.BINGX.value:
            self.broker = BingXBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        elif self.broker_type == BrokerType.BINANCE.value:
            self.broker = BinanceBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        elif self.broker_type == BrokerType.MEXC.value:
            self.broker = MEXCBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        elif self.broker_type == BrokerType.PHEMEX.value:
            self.broker = PhemexBrokerAdapter(config)
            self.broker_name = self.broker_type_enum.get_display_name()
        else:
            raise ValueError(
                f"Unsupported broker type: {self.broker_type}. "
                f"Supported types: {BrokerType.get_supported_types()}"
            )
    
    def _load_config_from_env(self, broker_type: str) -> Dict[str, Any]:
        """Load broker configuration from environment variables."""
        broker_enum = BrokerType.from_string(broker_type)

        if broker_enum == BrokerType.BINGX:
            config = {
                'api_key': os.getenv('BINGX_API_KEY'),
                'secret_key': os.getenv('BINGX_SECRET_KEY'),
                'passphrase': os.getenv('BINGX_PASSPHRASE', ''),
                'testnet': os.getenv('BINGX_TESTNET', 'true').lower() == 'true'
            }
        elif broker_enum == BrokerType.BINANCE:
            config = {
                'api_key': os.getenv('BINANCE_API_KEY'),
                'secret_key': os.getenv('BINANCE_SECRET_KEY'),
                'testnet': os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
            }
        elif broker_enum == BrokerType.MEXC:
            config = {
                'api_key': os.getenv('MEXC_API_KEY'),
                'secret_key': os.getenv('MEXC_SECRET_KEY'),
                'testnet': os.getenv('MEXC_TESTNET', 'true').lower() == 'true'
            }
        elif broker_enum == BrokerType.PHEMEX:
            config = {
                'api_key': os.getenv('PHEMEX_API_KEY'),
                'secret_key': os.getenv('PHEMEX_SECRET_KEY'),
                'testnet': os.getenv('PHEMEX_TESTNET', 'true').lower() == 'true'
            }
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")

        # Validate required configuration
        required_keys = ['api_key', 'secret_key']
        for key in required_keys:
            if not config.get(key):
                raise ValueError(
                    f"{broker_type.upper()}_{key.upper()} must be set in environment variables"
                )

        return config

    def execute_order(self, order: Order) -> str:
        """Execute an order through the configured broker."""
        try:
            self.logger.info(f"🎯 EXECUTING ORDER ON {self.broker_name}: {order}")
            order_id = self.broker.place_order(order)
            self.logger.info(f"✅ ORDER PLACED SUCCESSFULLY ON {self.broker_name}: {order_id}")
            return order_id
        except Exception as e:
            self.logger.error(f"❌ FAILED TO EXECUTE ORDER ON {self.broker_name}: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order through the configured broker."""
        try:
            self.logger.info(f"🔄 CANCELLING ORDER ON {self.broker_name}: {order_id}")
            # For now, we'll use a placeholder symbol - in real implementation, 
            # the order_id should be sufficient or you'd pass the symbol
            return self.broker.cancel_order(order_id, Symbol("BTCUSDT"))  # Placeholder
        except Exception as e:
            self.logger.error(f"❌ FAILED TO CANCEL ORDER ON {self.broker_name}: {e}")
            return False

    def get_execution_status(self, execution_id: str) -> str:
        """Get the status of an execution through the configured broker."""
        try:
            # In a real implementation, you'd need the symbol as well
            # For now, using placeholder - real implementation would track symbol with execution
            status = self.broker.get_order_status(execution_id, Symbol("BTCUSDT"))  # Placeholder
            return status
        except Exception as e:
            self.logger.error(f"❌ FAILED TO GET EXECUTION STATUS ON {self.broker_name}: {e}")
            return "error"

    def get_broker_name(self) -> str:
        """Get the name of the configured broker."""
        return self.broker_name

    def get_broker_type(self) -> str:
        """Get the type of the configured broker."""
        return self.broker_type

    def get_available_symbols(self) -> set:
        """Get available symbols from the configured broker."""
        # Ensure broker is connected before calling the method
        if hasattr(self.broker, 'connect') and not getattr(self.broker, 'connected', False):
            try:
                self.broker.connect()
            except Exception as e:
                self.logger.warning(f"Could not connect broker {self.broker_name} before getting available symbols: {e}")
                return set()

        if hasattr(self.broker, 'get_available_symbols'):
            return self.broker.get_available_symbols()
        else:
            # If the internal broker doesn't have this method, return empty set
            self.logger.warning(f"Broker {self.broker_name} does not support get_available_symbols method")
            return set()


def create_execution_service(broker_type: Optional[str] = None) -> ExecutionPort:
    """
    Factory function to create a broker execution service.

    Args:
        broker_type: Type of broker ('bingx', 'binance', 'mexc', 'phemex').
                    If None, will use DEFAULT_BROKER environment variable.

    Returns:
        Configured execution service instance
    """
    return BrokerExecutionService(broker_type=broker_type)


def create_execution_service_from_enum(broker_type_enum: Optional['BrokerType'] = None) -> ExecutionPort:
    """
    Factory function to create a broker execution service from BrokerType enum.

    Args:
        broker_type_enum: BrokerType enum value.
                         If None, will use DEFAULT_BROKER environment variable.

    Returns:
        Configured execution service instance
    """
    broker_type_str = broker_type_enum.value if broker_type_enum else None
    return BrokerExecutionService(broker_type=broker_type_str)