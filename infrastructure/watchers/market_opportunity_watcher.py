"""
Market Opportunity Watcher for auto-detection system.
Monitors markets continuously and identifies opportunities based on technical conditions.
Following correct architecture: Watchers only produce raw market observations.
"""
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.messaging.event_system import event_router

# Import services
from infrastructure.services.symbol_discovery_service import SymbolDiscoveryService
from infrastructure.services.symbol_validation_service import SymbolValidationService
from infrastructure.watchers.watcher_initialization_service import WatcherInitializationService
from infrastructure.watchers.monitoring_analysis_service import MonitoringAnalysisService


class MarketOpportunityWatcher:
    """Watches markets continuously to detect market observations and emit them to event system.
    Correct architecture: Watcher only emits MarketObservation events to external processing system."""

    def __init__(self, settings,
                 symbols: Optional[List[str]] = None,
                 opportunity_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                 auto_discover_symbols: bool = False,
                 comprehensive_logging: bool = True,
                 market_data_repo=None,
                 event_router=None):
        # Settings injected by the composition root (E1.T4); threaded to the symbol
        # services, watcher-init service, and the default-symbol fallback below.
        self._settings = settings
        self.auto_discover_symbols = auto_discover_symbols
        self.opportunity_callback = opportunity_callback
        self.logger = EnhancedLogger("MarketOpportunityWatcher", comprehensive_mode=comprehensive_logging)
        self.comprehensive_logging = comprehensive_logging
        self.is_running = False
        self.watchers = {}
        self.last_observations = {}
        self.monitoring_thread = None

        # Event router for proper architecture flow
        self.event_router = event_router if event_router else globals().get('event_router')

        self.market_data_repo = market_data_repo

        # Initialize services
        self.symbol_discovery_service = SymbolDiscoveryService(settings=self._settings, logger=self.logger)
        self.symbol_validation_service = SymbolValidationService(self.logger, data_config=self._settings.data)
        self.symbol_validation_service.market_data_repo = self.market_data_repo
        self.watcher_init_service = WatcherInitializationService(self._settings, self.logger, self.market_data_repo)
        self.monitoring_service = MonitoringAnalysisService(self.logger, self.event_router, self.market_data_repo)
        self.monitoring_service.auto_discover_symbols = self.auto_discover_symbols
        self.monitoring_service.on_update_symbols = self._update_symbol_list


        # If no symbols provided and auto-discovery is enabled, discover symbols dynamically
        if auto_discover_symbols and not symbols:
            discovered_symbols = self.symbol_discovery_service.discover_symbols_automatically()
            filtered_symbols = self.symbol_validation_service.filter_stablecoin_pairs(discovered_symbols)
            self.symbols = self.symbol_validation_service.validate_symbol_data_availability(filtered_symbols)
        elif symbols:
            # Convert symbol format if needed (e.g., BTC/USDT -> BTCUSDT)
            converted_symbols = []
            for s in symbols:
                # Check if it's already a Symbol object or a string
                if hasattr(s, 'value'):  # It's already a Symbol object
                    symbol_str = s.value
                else:  # It's a string
                    symbol_str = s

                # Convert from BTC/USDT format to BTCUSDT format if slash is present
                if '/' in symbol_str:
                    symbol_str = symbol_str.replace('/', '')

                converted_symbols.append(Symbol(symbol_str))
            filtered_symbols = self.symbol_validation_service.filter_stablecoin_pairs(converted_symbols)
            self.symbols = self.symbol_validation_service.validate_symbol_data_availability(filtered_symbols)
        else:
            # Use default symbols from environment variables or fallback to hard-coded defaults
            default_symbols = (self._settings.data.default_watchlist_symbols if self._settings.data and self._settings.data.default_watchlist_symbols else "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT").split(",")
            unfiltered_symbols = [Symbol(s.strip()) for s in default_symbols]
            filtered_symbols = self.symbol_validation_service.filter_stablecoin_pairs(unfiltered_symbols)
            self.symbols = self.symbol_validation_service.validate_symbol_data_availability(filtered_symbols)

        # Initialize watcher adapters for each symbol
        self._initialize_watchers()

    def _initialize_watchers(self):
        """Initialize watcher adapters for each symbol using the watcher initialization service."""
        # Stop old watchers if they exist to prevent orphan threads and connection leaks
        if hasattr(self, 'watchers') and self.watchers:
            self.logger.info("Stopping old watchers before initializing new ones...")
            for symbol_watchers in self.watchers.values():
                for watcher in symbol_watchers.values():
                    if hasattr(watcher, 'stop'):
                        try:
                            watcher.stop()
                        except Exception as e:
                            self.logger.warning(f"Error stopping old watcher: {e}")

        # Use the watcher initialization service to handle the complex initialization logic
        self.watchers, self.broker_service = self.watcher_init_service.initialize_watchers(
            self.symbols,
            getattr(self, '_watcher_specific_symbols', None)
        )
        
        # Set the watchers and symbols in the monitoring service
        self.monitoring_service.set_watchers_and_symbols(self.watchers, self.symbols)

        # Wire broker_service to validation service for future updates
        self.symbol_validation_service.broker_service = self.broker_service



    def start_monitoring(self):
        """Start continuous market monitoring."""
        # Delegate to the monitoring service
        self.monitoring_service.start_monitoring()

    def stop_monitoring(self):
        """Stop market monitoring."""
        # Delegate to the monitoring service
        self.monitoring_service.stop_monitoring()

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the watcher."""
        return {
            'is_running': self.is_running,
            'monitored_symbols': [s.value for s in self.symbols],
            'watcher_count': sum(len(w) for w in self.watchers.values()) if self.watchers else 0,
            'last_observations': {k: list(v.keys()) for k, v in self.last_observations.items()},  # Updated to observations
            'timestamp': datetime.now().isoformat()
        }

    def _update_symbol_list(self):
        """Callback to dynamically update and initialize watchers for newly discovered symbols."""
        if not self.auto_discover_symbols:
            return
        
        self.logger.info("🔄 Refreshing symbols list dynamically...")
        try:
            discovered_symbols = self.symbol_discovery_service.discover_symbols_automatically()
            filtered_symbols = self.symbol_validation_service.filter_stablecoin_pairs(discovered_symbols)
            new_symbols = self.symbol_validation_service.validate_symbol_data_availability(filtered_symbols)
            
            # Check if symbols list has changed
            current_set = set(s.value for s in self.symbols)
            new_set = set(s.value for s in new_symbols)
            
            if current_set != new_set:
                self.logger.info(f"🔄 Watchlist changed! Previous: {list(current_set)}, New: {list(new_set)}")
                self.symbols = new_symbols
                self._initialize_watchers()
            else:
                self.logger.info("🔄 Watchlist unchanged, no updates needed.")
        except Exception as e:
            self.logger.error(f"Error updating dynamic symbol list: {e}")
