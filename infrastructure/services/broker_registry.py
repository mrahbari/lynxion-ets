"""
Broker Registry - Singleton pattern for managing shared broker service instances
This prevents duplicate initialization of the same broker services across different components
"""
import threading
from typing import Dict, Optional, Any
from domain.ports.execution_ports import ExecutionPort
from domain.ports.data_ports import DataProviderPort


class BrokerRegistry:
    """Singleton registry for managing shared broker service instances"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._broker_services: Dict[str, ExecutionPort] = {}
            self._historical_data_providers: Dict[str, DataProviderPort] = {}
            self._lock = threading.RLock()  # Use RLock to prevent deadlocks
            self.initialized = True

    def get_execution_service(self,
                            broker_type: Optional[str] = None,
                            use_multi_broker: bool = True,
                            primary_broker: Optional[str] = None) -> ExecutionPort:
        """Get or create a shared execution service instance"""
        # Create a unique key based on the configuration
        config_key = f"exec_{broker_type or 'default'}_{use_multi_broker}_{primary_broker or 'default'}"

        with self._lock:
            if config_key not in self._broker_services:
                # Import here to avoid circular imports
                from infrastructure.services.broker_execution_service import create_execution_service
                service = create_execution_service(
                    broker_type=broker_type,
                    use_multi_broker=use_multi_broker,
                    primary_broker=primary_broker
                )
                self._broker_services[config_key] = service

                # Log that we're creating a new instance
                import shared.logger as logger_module
                logger = logger_module.EnhancedLogger("BrokerRegistry")
                logger.info(f"🆕 Created new execution service instance for key: {config_key}")

            return self._broker_services[config_key]

    def get_historical_data_provider(self,
                                   csv_base_path: Optional[str] = None,
                                   download_enabled: bool = True,
                                   broker_service: Optional[ExecutionPort] = None,
                                   historical_data_source: Optional[str] = None,
                                   fallback_sources: Optional[list] = None) -> DataProviderPort:
        """Get or create a shared historical data provider instance"""
        # Create a unique key based on the configuration
        broker_key = id(broker_service) if broker_service else 'none'
        config_key = f"data_{csv_base_path or 'default'}_{download_enabled}_{historical_data_source or 'default'}_{broker_key}"

        with self._lock:
            if config_key not in self._historical_data_providers:
                # Import here to avoid circular imports
                from infrastructure.data.enhanced_data_provider import create_enhanced_data_provider
                provider = create_enhanced_data_provider(
                    csv_base_path=csv_base_path,
                    download_enabled=download_enabled,
                    broker_service=broker_service,
                    historical_data_source=historical_data_source,
                    fallback_sources=fallback_sources
                )
                self._historical_data_providers[config_key] = provider

                # Log that we're creating a new instance
                import shared.logger as logger_module
                logger = logger_module.EnhancedLogger("BrokerRegistry")
                logger.info(f"🆕 Created new historical data provider instance for key: {config_key}")

            return self._historical_data_providers[config_key]

    def get_all_services(self):
        """Get all registered services for debugging and monitoring"""
        with self._lock:
            return {
                'broker_services': dict(self._broker_services),
                'data_providers': dict(self._historical_data_providers)
            }

    def clear_registry(self):
        """Clear all registered instances (for testing purposes)"""
        with self._lock:
            # Close connections before clearing to free up resources
            for service in self._broker_services.values():
                if hasattr(service, 'broker') and hasattr(service.broker, 'disconnect'):
                    try:
                        service.broker.disconnect()
                    except Exception as e:
                        import shared.logger as logger_module
                        logger = logger_module.EnhancedLogger("BrokerRegistry")
                        logger.warning(f"Error disconnecting broker service: {e}")

            self._broker_services.clear()
            self._historical_data_providers.clear()


# Global registry instance
broker_registry = BrokerRegistry()