"""
Watcher Initialization Module for Market Opportunity Watcher
Handles initialization and management of watcher instances
"""
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.watchers.watcher_factory import WatcherFactory, WatcherType
from application.configs.hexagonal_settings import config as hexagonal_config
from infrastructure.services.broker_execution_service import create_execution_service


class WatcherInitializationService:
    """Service class for initializing and managing watcher instances."""
    
    def __init__(self, logger: EnhancedLogger = None, market_data_repo=None):
        self.logger = logger or EnhancedLogger("WatcherInitializationService")
        self.market_data_repo = market_data_repo
    
    def initialize_watchers(self, symbols: List[Symbol], watcher_specific_symbols: Optional[Dict] = None):
        """Initialize watcher adapters for each symbol based on which watcher discovered it - only if enabled."""
        # Create a mapping of symbols to their primary watcher based on discovery
        symbol_to_primary_watcher = {}

        # If we're in auto-discovery mode, we know which watcher discovered which symbols
        if watcher_specific_symbols:
            for watcher_type, symbols_list in watcher_specific_symbols.items():
                # Check if this watcher type is enabled
                env_var = f"{watcher_type.upper()}_WATCHER_ENABLED"
                if os.getenv(env_var, 'true').lower() == 'true':
                    for symbol in symbols_list:
                        # Assign this watcher as the primary watcher for this symbol
                        if symbol not in symbol_to_primary_watcher:
                            symbol_to_primary_watcher[symbol] = set()
                        symbol_to_primary_watcher[symbol].add(watcher_type)

        # Initialize broker service with all available brokers
        broker_service = create_execution_service(use_multi_broker=True)

        watchers = {}
        for symbol in symbols:
            symbol_watchers = {}

            # Check each watcher type before creating to avoid unnecessary instantiation
            # Only create watchers that are relevant to this symbol or if it's a general watcher

            # Market Pulse watcher
            if os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("MarketPulse")

                # Check if this symbol was discovered by market pulse watcher
                if (symbol.value in symbol_to_primary_watcher and
                        'market_pulse' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['market_pulse'] = WatcherFactory.create_watcher(
                        WatcherType.MARKET_PULSE,
                        "MarketPulse",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"MarketPulse assigned to {symbol.value} (discovered by MarketPulse) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="market_pulse",
                            discovery_source="market_pulse",
                            broker=target_broker
                        )
                else:  # If no specific mapping (fallback to original behavior)
                    symbol_watchers['market_pulse'] = WatcherFactory.create_watcher(
                        WatcherType.MARKET_PULSE,
                        "MarketPulse",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # Volatility watcher
            if os.getenv('VOLATILITY_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("Volatility")
                # Check if this symbol was discovered by volatility watcher
                if (symbol.value in symbol_to_primary_watcher and
                        'volatility' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['volatility'] = WatcherFactory.create_watcher(
                        WatcherType.VOLATILITY,
                        "Volatility",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"Volatility assigned to {symbol.value} (discovered by Volatility) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="volatility",
                            discovery_source="volatility",
                            broker=target_broker
                        )
                else:  # If no specific mapping (fallback to original behavior)
                    symbol_watchers['volatility'] = WatcherFactory.create_watcher(
                        WatcherType.VOLATILITY,
                        "Volatility",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # Trend MTF watcher
            if os.getenv('TREND_MTF_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("TrendMTF")
                if (symbol.value in symbol_to_primary_watcher and
                        'trend_mtf' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['trend_mtf'] = WatcherFactory.create_watcher(
                        WatcherType.TREND_MTF,
                        "TrendMTF",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"TrendMTF assigned to {symbol.value} (discovered by TrendMTF) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="trend_mtf",
                            discovery_source="trend_mtf",
                            broker=target_broker
                        )
                else:
                    symbol_watchers['trend_mtf'] = WatcherFactory.create_watcher(
                        WatcherType.TREND_MTF,
                        "TrendMTF",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # Anomaly ML watcher
            if os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("AnomalyML")
                if (symbol.value in symbol_to_primary_watcher and
                        'anomaly_ml' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['anomaly_ml'] = WatcherFactory.create_watcher(
                        WatcherType.ANOMALY_ML,
                        "AnomalyML",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"AnomalyML assigned to {symbol.value} (discovered by AnomalyML) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="anomaly_ml",
                            discovery_source="anomaly_ml",
                            broker=target_broker
                        )
                else:
                    symbol_watchers['anomaly_ml'] = WatcherFactory.create_watcher(
                        WatcherType.ANOMALY_ML,
                        "AnomalyML",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # OrderFlow WS watcher
            if os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("OrderFlowWS")
                if (symbol.value in symbol_to_primary_watcher and
                        'orderflow_ws' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['orderflow_ws'] = WatcherFactory.create_watcher(
                        WatcherType.ORDERFLOW_WS,
                        "OrderFlowWS",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"OrderFlowWS assigned to {symbol.value} (discovered by OrderFlowWS) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="orderflow_ws",
                            discovery_source="orderflow_ws",
                            broker=target_broker
                        )
                else:
                    symbol_watchers['orderflow_ws'] = WatcherFactory.create_watcher(
                        WatcherType.ORDERFLOW_WS,
                        "OrderFlowWS",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # CMC Screener watcher
            if os.getenv('CMC_SCREENER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("CMCScreener")
                if (symbol.value in symbol_to_primary_watcher and
                        'cmc_screener' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['cmc_screener'] = WatcherFactory.create_watcher(
                        WatcherType.CMC_SCREEN,
                        "CMCScreener",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"CMCScreener assigned to {symbol.value} (discovered by CMCScreener) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="cmc_screener",
                            discovery_source="cmc_screener",
                            broker=target_broker
                        )
                else:
                    symbol_watchers['cmc_screener'] = WatcherFactory.create_watcher(
                        WatcherType.CMC_SCREEN,
                        "CMCScreener",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # Funding Rate watcher
            if os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("FundingRate")
                if (symbol.value in symbol_to_primary_watcher and
                        'funding_rate' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['funding_rate'] = WatcherFactory.create_watcher(
                        WatcherType.FUNDING_RATE,
                        "FundingRate",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"FundingRate assigned to {symbol.value} (discovered by FundingRate) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="funding_rate",
                            discovery_source="funding_rate",
                            broker=target_broker
                        )
                else:
                    symbol_watchers['funding_rate'] = WatcherFactory.create_watcher(
                        WatcherType.FUNDING_RATE,
                        "FundingRate",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # Liquidity watcher
            if os.getenv('LIQUIDITY_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("Liquidity")
                if (symbol.value in symbol_to_primary_watcher and
                        'liquidity' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['liquidity'] = WatcherFactory.create_watcher(
                        WatcherType.LIQUIDITY,
                        "Liquidity",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"Liquidity assigned to {symbol.value} (discovered by Liquidity) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="liquidity",
                            discovery_source="liquidity",
                            broker=target_broker
                        )
                else:
                    symbol_watchers['liquidity'] = WatcherFactory.create_watcher(
                        WatcherType.LIQUIDITY,
                        "Liquidity",
                        symbol.value,
                        broker_service=broker_service,
                        target_broker=target_broker
                    )

            # Historical Candle watcher
            if os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("HistoricalCandle")

                if (symbol.value in symbol_to_primary_watcher and
                        'historical_candle' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['historical_candle'] = WatcherFactory.create_watcher(
                        WatcherType.HISTORICAL_CANDLE,
                        "HistoricalCandle",
                        symbol.value,
                        broker_service=broker_service
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"HistoricalCandle assigned to {symbol.value} (discovered by HistoricalCandle) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="historical_candle",
                            discovery_source="historical_candle",
                            broker=target_broker
                        )
                else:
                    symbol_watchers['historical_candle'] = WatcherFactory.create_watcher(
                        WatcherType.HISTORICAL_CANDLE,
                        "HistoricalCandle",
                        symbol.value,
                        broker_service=broker_service
                    )

            # Tick Watcher
            if os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true':
                # Get target broker for this watcher from configuration
                target_broker = hexagonal_config.get_broker_for_watcher("TickWatcher")
                if (symbol.value in symbol_to_primary_watcher and
                        'tick_watcher' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['tick_watcher'] = WatcherFactory.create_watcher(
                        WatcherType.TICK,
                        "TickWatcher",
                        symbol.value,
                        broker_service=broker_service
                    )
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"TickWatcher assigned to {symbol.value} (discovered by TickWatcher) on broker {target_broker}",
                            symbol=symbol.value,
                            watcher="tick_watcher",
                            discovery_source="tick_watcher",
                            broker=target_broker
                        )
                else:
                    # Use the market data repo instead of execution service since we removed direct service access
                    symbol_watchers['tick_watcher'] = WatcherFactory.create_watcher(
                        WatcherType.TICK,
                        "TickWatcher",
                        symbol.value,
                        broker_service=broker_service
                    )

            watchers[symbol.value] = symbol_watchers

            # Start only the enabled watchers - double check enabled status
            for watcher_name, watcher in symbol_watchers.items():
                # Double-check the watcher's enabled status before starting
                if getattr(watcher, 'enabled', True):
                    watcher.start()

        # Store the broker service as an instance variable so it can be reused in _update_symbol_list
        return watchers, broker_service