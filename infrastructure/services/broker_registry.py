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
                            settings,
                            broker_type: Optional[str] = None,
                            use_multi_broker: bool = True,
                            primary_broker: Optional[str] = None) -> ExecutionPort:
        """Get or create a shared execution service instance.

        ``settings`` is injected by the composition root (E1.T4) and forwarded to
        the execution-service factory; this registry no longer imports settings.
        """
        # Create a unique key based on the configuration
        config_key = f"exec_{broker_type or 'default'}_{use_multi_broker}_{primary_broker or 'default'}"

        with self._lock:
            if config_key not in self._broker_services:
                # Import here to avoid circular imports
                from infrastructure.services.broker_execution_service import create_execution_service
                service = create_execution_service(
                    settings=settings,
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
                                   settings,
                                   csv_base_path: Optional[str] = None,
                                   download_enabled: bool = True,
                                   broker_service: Optional[ExecutionPort] = None,
                                   historical_data_source: Optional[str] = None,
                                   fallback_sources: Optional[list] = None) -> DataProviderPort:
        """Get or create a shared historical data provider instance.

        ``settings`` is injected by the composition root (E1.T4) and forwarded to
        the data-provider factory; this registry no longer imports settings itself.
        """
        # Create a unique key based on the configuration
        broker_key = id(broker_service) if broker_service else 'none'
        config_key = f"data_{csv_base_path or 'default'}_{download_enabled}_{historical_data_source or 'default'}_{broker_key}"

        with self._lock:
            if config_key not in self._historical_data_providers:
                # Import here to avoid circular imports
                from infrastructure.data.enhanced_data_provider import create_enhanced_data_provider
                provider = create_enhanced_data_provider(
                    settings=settings,
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
                if hasattr(service, 'broker'):
                    if hasattr(service.broker, 'disconnect'):
                        try:
                            service.broker.disconnect()
                        except Exception as e:
                            import shared.logger as logger_module
                            logger = logger_module.EnhancedLogger("BrokerRegistry")
                            logger.warning(f"Error disconnecting broker service: {e}")
                    elif hasattr(service.broker, 'session') and hasattr(service.broker.session, 'close'):
                        # Close session if available (for HTTP-based brokers)
                        try:
                            service.broker.session.close()
                        except Exception as e:
                            import shared.logger as logger_module
                            logger = logger_module.EnhancedLogger("BrokerRegistry")
                            logger.warning(f"Error closing broker session: {e}")

            self._broker_services.clear()
            self._historical_data_providers.clear()


# Module-level instantiation retired (E2.T6): access is now mediated by the
# composition root (bootstrap/container.py registers ``broker_registry``). This
# lazy accessor defers creation past import for backward-compatible callers.
#
# NOTE: broker_registry INTENTIONALLY remains a single instance per process. It
# guarantees one shared execution service / broker session per run (relied upon
# by E2.T5.3); making it independent per container would regress that safety
# guarantee. ``BrokerRegistry.__new__`` enforces the process singleton, so the
# container factory and this accessor return the same instance.
def __getattr__(name):
    if name == "broker_registry":
        return BrokerRegistry()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")