"""
Market Opportunity Watcher for auto-detection system.
Monitors markets continuously and identifies opportunities based on technical conditions.
Following correct architecture: Watchers only produce raw market observations.
"""
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from domain.entities.signal_entities import MarketObservation, InterpretedSignal, FusedSignal, ExecutionIntent
from domain.value_objects import Symbol
from infrastructure.watchers.base_watcher import BaseWatcher
from shared.logger import EnhancedLogger
from domain.ports.engine_ports import SignalPort
from domain.ports.engine_ports import FusionPort
from shared.event_system import event_router

# Import services
from infrastructure.services.symbol_discovery_service import SymbolDiscoveryService
from infrastructure.services.symbol_validation_service import SymbolValidationService
from infrastructure.watchers.watcher_initialization_service import WatcherInitializationService
from infrastructure.watchers.monitoring_analysis_service import MonitoringAnalysisService

# Import the symbol validator
from utils.symbol_validator import symbol_validator
from application.configs.configs import Configs
from utils.config_helper import cfg_get, cfg_get_bool, cfg_get_int, cfg_get_float, cfg_get_list, cfg_get_str


class MarketOpportunityWatcher:
    """Watches markets continuously to detect market observations and emit them to event system.
    Correct architecture: Watcher only emits MarketObservation events to external processing system."""

    def __init__(self, symbols: Optional[List[str]] = None,
                 opportunity_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                 auto_discover_symbols: bool = False,
                 comprehensive_logging: bool = True,
                 market_data_repo=None,
                 event_router=None):
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
        self.symbol_discovery_service = SymbolDiscoveryService(self.logger)
        self.symbol_validation_service = SymbolValidationService(self.logger)
        self.watcher_init_service = WatcherInitializationService(self.logger, self.market_data_repo)
        self.monitoring_service = MonitoringAnalysisService(self.logger, self.event_router, self.market_data_repo)

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
            default_symbols = (Configs.data.default_watchlist_symbols if Configs.data and Configs.data.default_watchlist_symbols else "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT").split(",")
            unfiltered_symbols = [Symbol(s.strip()) for s in default_symbols]
            filtered_symbols = self.symbol_validation_service.filter_stablecoin_pairs(unfiltered_symbols)
            self.symbols = self.symbol_validation_service.validate_symbol_data_availability(filtered_symbols)

        # Initialize watcher adapters for each symbol
        self._initialize_watchers()

    def _filter_stablecoin_pairs(self, symbols):
        """Filter out stablecoin-stablecoin pairs from the symbol list."""
        import os
        import re

        # Check if filtering is enabled
        filter_stablecoin_pairs = cfg_get_bool(Configs.data, 'filter_out_stablecoin_pairs', True)

        if not filter_stablecoin_pairs:
            return symbols

        # Get allowed stablecoins from config
        allowed_stablecoins_str = cfg_get_str(Configs.data, 'allowed_stablecoins', 'USDT,BUSD,USDC,DAI,PAX,TUSD,USDD,FDUSD')
        allowed_stablecoins = [s.strip().upper() for s in allowed_stablecoins_str.split(',')]

        filtered_symbols = []
        for symbol in symbols:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            symbol_upper = symbol_str.upper()

            # Parse symbol to extract base and quote currencies
            base_currency = ""
            quote_currency = ""

            # Try to identify quote currency by looking for known stablecoins at the end
            # Sort stablecoins by length descending to match longer ones first (to avoid partial matches)
            sorted_stables = sorted(allowed_stablecoins, key=len, reverse=True)
            for stable in sorted_stables:
                stable_upper = stable.upper()
                if symbol_upper.endswith(stable_upper):
                    base_part = symbol_upper[:-len(stable_upper)]
                    if base_part:  # Make sure there's a base currency part
                        base_currency = symbol_str[:-len(stable)]  # Keep original case for logging
                        quote_currency = stable
                        break

            # If we couldn't identify by ending, try to split by common separators
            if not base_currency and not quote_currency:
                if '-' in symbol_str:
                    parts = symbol_str.split('-')
                    if len(parts) == 2:
                        base_currency, quote_currency = parts[0], parts[1]
                elif '/' in symbol_str:
                    parts = symbol_str.split('/')
                    if len(parts) == 2:
                        base_currency, quote_currency = parts[0], parts[1]

            # Check if both base and quote are stablecoins (stablecoin-stablecoin pair)
            if base_currency and quote_currency:
                base_upper = base_currency.upper()
                quote_upper = quote_currency.upper()

                # If both are stablecoins and different, it's a stablecoin pair to filter out
                if base_upper in allowed_stablecoins and quote_upper in allowed_stablecoins and base_upper != quote_upper:
                    self.logger.info(f"🪙 STABLECOIN FILTER: Skipping {symbol_str} (base: {base_currency}, quote: {quote_currency})")
                    continue  # Skip this symbol

                # Also check for same currency pair (e.g., USDCUSDC)
                if base_upper == quote_upper:
                    self.logger.info(f"🪙 STABLECOIN FILTER: Skipping {symbol_str} (same currency)")
                    continue  # Skip this symbol

            # Check using regex pattern if provided - improved to catch more stablecoin pairs
            excluded_pattern = os.getenv('EXCLUDED_SYMBOLS_PATTERN', r'(?:USDT|USDC|BUSD|DAI|PAX|TUSD|USDD|FDUSD)(?:USDT|USDC|BUSD|DAI|PAX|TUSD|USDD|FDUSD)|BTC/BTC|ETH/ETH')
            if re.search(excluded_pattern, symbol_upper):
                self.logger.info(f"🚫 PATTERN FILTER: Skipping {symbol_str} (matches exclusion pattern)")
                continue  # Skip this symbol

            # If we reach here, the symbol passed all filters
            filtered_symbols.append(symbol)

        # Log the filtering results
        original_count = len(symbols)
        filtered_count = len(filtered_symbols)
        if original_count != filtered_count:
            self.logger.info(f"📊 SYMBOL FILTERING: {original_count} -> {filtered_count} symbols after stablecoin filtering")

        return filtered_symbols

    def _validate_symbol_data_availability(self, symbols):
        """Validate that symbols have data available on exchanges before processing."""
        validated_symbols = []

        # Check if data validation is enabled
        validate_data_availability = os.getenv('VALIDATE_SYMBOL_DATA_AVAILABILITY', 'true').lower() == 'true'

        if not validate_data_availability:
            # Still apply approved symbol validation even if data availability validation is disabled
            for symbol in symbols:
                symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
                if symbol_validator.is_symbol_approved(symbol):
                    validated_symbols.append(symbol)
                else:
                    self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Skipping...")
            return validated_symbols

        self.logger.info(f"🔍 Validating data availability and approved status for {len(symbols)} symbols...")

        for symbol in symbols:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

            # First check if symbol is in approved list
            if not symbol_validator.is_symbol_approved(symbol):
                self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Skipping...")
                continue

            try:
                # Check if the symbol is available in the market data repository
                if self.market_data_repo and hasattr(self.market_data_repo, 'is_symbol_available'):
                    is_available = self.market_data_repo.is_symbol_available(symbol_str)

                    if is_available:
                        validated_symbols.append(symbol)
                        self.logger.debug(f"✅ Data available for {symbol_str}")
                    else:
                        self.logger.warning(f"⚠️ Data not available for {symbol_str}, skipping...")
                else:
                    # If no market data repo is available, try to validate using broker service
                    if hasattr(self, 'broker_service') and self.broker_service:
                        available_symbols = self.broker_service.get_available_symbols()

                        if symbol_str in available_symbols:
                            validated_symbols.append(symbol)
                            self.logger.debug(f"✅ Symbol available on broker: {symbol_str}")
                        else:
                            self.logger.warning(f"⚠️ Symbol not available on broker: {symbol_str}, skipping...")
                    else:
                        # If no validation method is available, assume symbol is valid
                        validated_symbols.append(symbol)
                        self.logger.warning(f"⚠️ No validation method available for {symbol_str}, assuming valid...")

            except Exception as e:
                self.logger.warning(f"⚠️ Error validating data for {symbol_str}: {e}, skipping...")
                continue

        original_count = len(symbols)
        validated_count = len(validated_symbols)

        if original_count != validated_count:
            self.logger.info(f"📊 DATA AVAILABILITY & APPROVAL VALIDATION: {original_count} -> {validated_count} symbols after validation")

        return validated_symbols

    def _discover_symbols_automatically(self) -> List[Symbol]:
        """Dynamically discover symbols to monitor based on market conditions or other criteria."""
        self.logger.info("🔍 Discovering symbols to monitor automatically...")

        # Check which watcher types are enabled to determine appropriate discovery method
        market_pulse_enabled = os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true'
        volatility_enabled = os.getenv('VOLATILITY_WATCHER_ENABLED', 'true').lower() == 'true'
        trend_mtf_enabled = os.getenv('TREND_MTF_WATCHER_ENABLED', 'true').lower() == 'true'
        anomaly_ml_enabled = os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'true').lower() == 'true'
        orderflow_ws_enabled = os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'true').lower() == 'true'
        cmc_screener_enabled = os.getenv('CMC_SCREENER_ENABLED', 'true').lower() == 'true'
        funding_rate_enabled = os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true'
        liquidity_enabled = os.getenv('LIQUIDITY_WATCHER_ENABLED', 'true').lower() == 'true'
        historical_candle_enabled = os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true'
        tick_watcher_enabled = os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true'

        # If multiple watchers are enabled, use comprehensive discovery that covers all types
        enabled_watchers = []
        if market_pulse_enabled:
            enabled_watchers.append('market_pulse')
        if volatility_enabled:
            enabled_watchers.append('volatility')
        if trend_mtf_enabled:
            enabled_watchers.append('trend_mtf')
        if anomaly_ml_enabled:
            enabled_watchers.append('anomaly_ml')
        if orderflow_ws_enabled:
            enabled_watchers.append('orderflow_ws')
        if funding_rate_enabled:
            enabled_watchers.append('funding_rate')
        if liquidity_enabled:
            enabled_watchers.append('liquidity')
        if historical_candle_enabled:
            enabled_watchers.append('historical_candle')
        if cmc_screener_enabled:
            enabled_watchers.append('cmc_screener')
        if tick_watcher_enabled:
            enabled_watchers.append('tick_watcher')

        # Check which watcher types are enabled to determine appropriate discovery method
        market_pulse_enabled = os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true'
        volatility_enabled = os.getenv('VOLATILITY_WATCHER_ENABLED', 'true').lower() == 'true'
        trend_mtf_enabled = os.getenv('TREND_MTF_WATCHER_ENABLED', 'true').lower() == 'true'
        anomaly_ml_enabled = os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'true').lower() == 'true'
        orderflow_ws_enabled = os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'true').lower() == 'true'
        cmc_screener_enabled = os.getenv('CMC_SCREENER_ENABLED', 'true').lower() == 'true'
        funding_rate_enabled = os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true'
        liquidity_enabled = os.getenv('LIQUIDITY_WATCHER_ENABLED', 'true').lower() == 'true'
        historical_candle_enabled = os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true'
        tick_watcher_enabled = os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true'

        # If multiple watchers are enabled, use comprehensive discovery that covers all types
        enabled_watchers = []
        if market_pulse_enabled:
            enabled_watchers.append('market_pulse')
        if volatility_enabled:
            enabled_watchers.append('volatility')
        if trend_mtf_enabled:
            enabled_watchers.append('trend_mtf')
        if anomaly_ml_enabled:
            enabled_watchers.append('anomaly_ml')
        if orderflow_ws_enabled:
            enabled_watchers.append('orderflow_ws')
        if funding_rate_enabled:
            enabled_watchers.append('funding_rate')
        if liquidity_enabled:
            enabled_watchers.append('liquidity')
        if historical_candle_enabled:
            enabled_watchers.append('historical_candle')
        if cmc_screener_enabled:
            enabled_watchers.append('cmc_screener')
        if tick_watcher_enabled:
            enabled_watchers.append('tick_watcher')

        # When multiple watchers are enabled, we want to ensure comprehensive coverage
        # Rather than choosing one discovery method, we should combine results from multiple discovery methods
        # to ensure symbols relevant to all watcher types are included
        watcher_specific_symbols = {}
        all_discovered_symbols = set()

        # Add symbols from each enabled watcher type's specific discovery method
        for watcher_type in enabled_watchers:
            if watcher_type == 'market_pulse':
                symbols = self._discover_trend_oriented_symbols()  # Use appropriate discovery method
            elif watcher_type == 'volatility':
                symbols = self._discover_volatility_oriented_symbols()
            elif watcher_type == 'trend_mtf':
                symbols = self._discover_trend_oriented_symbols()
            elif watcher_type == 'anomaly_ml':
                symbols = self._discover_anomaly_oriented_symbols()
            elif watcher_type == 'orderflow_ws':
                symbols = self._discover_orderflow_oriented_symbols()
            elif watcher_type == 'funding_rate':
                symbols = self._discover_funding_oriented_symbols()
            elif watcher_type == 'liquidity':
                symbols = self._discover_liquidity_oriented_symbols()
            elif watcher_type == 'historical_candle':
                symbols = self._discover_historical_candle_oriented_symbols()
            elif watcher_type == 'cmc_screener':
                symbols = self._discover_by_market_cap()
            elif watcher_type == 'tick_watcher':
                symbols = self._discover_tick_oriented_symbols()
            else:
                symbols = self._discover_by_market_cap()

            # Track what symbols each watcher discovered
            watcher_specific_symbols[watcher_type] = symbols
            all_discovered_symbols.update(symbols)

            # Log what symbols this specific watcher discovered
            if symbols:
                self.logger.info(
                    f"🔍 {watcher_type.upper()} WATCHER DISCOVERED: {len(symbols)} symbols - {symbols[:5]}{'...' if len(symbols) > 5 else ''}",
                    watcher_type=watcher_type,
                    symbols_discovered=len(symbols),
                    sample_symbols=symbols[:5])

        # Store the original set of discovered symbols before adding general symbols
        original_discovered_symbols = set(all_discovered_symbols)

        # Also add symbols from general market discovery to ensure comprehensive coverage
        general_symbols = self._discover_by_market_cap()
        all_discovered_symbols.update(general_symbols)

        # Add general symbols to an appropriate watcher category for tracking and logging
        # Use 'cmc_screener' as the general discovery method since it uses CMC API
        if general_symbols:
            if 'cmc_screener' not in watcher_specific_symbols:
                watcher_specific_symbols['cmc_screener'] = []
            # Add only new symbols that weren't already discovered by other watchers
            new_general_symbols = [sym for sym in general_symbols if sym not in original_discovered_symbols]
            watcher_specific_symbols['cmc_screener'].extend(new_general_symbols)

            # Log the general discovery symbols that were added
            if new_general_symbols:
                self.logger.info(
                    f"🔍 CMC SCREENER DISCOVERED: {len(new_general_symbols)} additional symbols from general market discovery - {new_general_symbols[:5]}{'...' if len(new_general_symbols) > 5 else ''}",
                    watcher_type='cmc_screener',
                    symbols_discovered=len(new_general_symbols),
                    sample_symbols=new_general_symbols[:5])

        discovered_symbols = list(all_discovered_symbols)

        # Store the watcher-specific symbols for later use in _initialize_watchers
        self._watcher_specific_symbols = watcher_specific_symbols

        # Log the combined symbol set
        self.logger.info(
            f"📊 COMBINED SYMBOLS: {len(discovered_symbols)} total symbols after combining {len(enabled_watchers)} watcher types",
            total_symbols=len(discovered_symbols),
            watcher_count=len(enabled_watchers),
            watcher_specific=watcher_specific_symbols)

        # If no specific discovery method worked, fall back to price activity
        if not discovered_symbols:
            price_activity_symbols = self._discover_by_price_activity()
            if price_activity_symbols:
                discovered_symbols = price_activity_symbols

                # Add price activity symbols to the cmc_screener category and log them
                if hasattr(self, '_watcher_specific_symbols') and 'cmc_screener' in self._watcher_specific_symbols:
                    self._watcher_specific_symbols['cmc_screener'].extend(price_activity_symbols)

                    # Log the price activity symbols that were added
                    self.logger.info(
                        f"🔍 CMC SCREENER DISCOVERED: {len(price_activity_symbols)} price activity symbols - {price_activity_symbols[:5]}{'...' if len(price_activity_symbols) > 5 else ''}",
                        watcher_type='cmc_screener',
                        symbols_discovered=len(price_activity_symbols),
                        sample_symbols=price_activity_symbols[:5])

        # If still no symbols found, use fallback symbols
        if not discovered_symbols:
            fallback_symbols_str = os.getenv("FALLBACK_WATCHLIST_SYMBOLS",
                                             "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,AVAXUSDT,TRXUSDT,DOTUSDT,LINKUSDT")
            fallback_symbols = [s.strip() for s in fallback_symbols_str.split(",")]
            discovered_symbols = fallback_symbols

            # Add fallback symbols to the cmc_screener category and log them
            if fallback_symbols and hasattr(self, '_watcher_specific_symbols') and 'cmc_screener' in self._watcher_specific_symbols:
                self._watcher_specific_symbols['cmc_screener'].extend(fallback_symbols)

                # Log the fallback symbols that were added
                self.logger.info(
                    f"🔍 CMC SCREENER DISCOVERED: {len(fallback_symbols)} fallback symbols - {fallback_symbols[:5]}{'...' if len(fallback_symbols) > 5 else ''}",
                    watcher_type='cmc_screener',
                    symbols_discovered=len(fallback_symbols),
                    sample_symbols=fallback_symbols[:5])

        # Filter out stablecoin-to-stablecoin pairs (e.g., USDTUSDT, USDCUSDT, etc.)
        filtered_symbols = self._filter_stablecoin_pairs(discovered_symbols)

        # Filter symbols and handle invalid ones gracefully
        valid_symbols = []
        for symbol in filtered_symbols:
            try:
                # Check if it's already a Symbol object or a string
                if isinstance(symbol, str):
                    # If it's a string, validate by creating a Symbol object
                    Symbol(symbol)  # This will raise ValueError if invalid
                    valid_symbols.append(symbol)
                elif hasattr(symbol, 'value'):  # It's already a Symbol object
                    # Just append the Symbol object directly
                    valid_symbols.append(symbol)
                else:
                    # Unknown type, skip it
                    self.logger.warning(f"Skipping invalid symbol of unknown type: {symbol}")
                    continue
            except ValueError:
                # Log the invalid symbol but continue processing others
                self.logger.warning(f"Skipping invalid symbol: {symbol}")
                continue

        self.logger.info(f"✅ Auto-discovered {len(valid_symbols)} symbols to monitor: {valid_symbols}")
        # Convert to Symbol objects only for valid ones (strings) and keep Symbol objects as-is
        final_symbols = []
        for symbol in valid_symbols:
            if isinstance(symbol, str):
                final_symbols.append(Symbol(symbol))
            else:
                final_symbols.append(symbol)  # Already a Symbol object

        return final_symbols

    def _discover_trend_oriented_symbols(self) -> List[str]:
        """Discover symbols with strong trend characteristics for trend watchers"""
        try:
            # This would connect to exchange APIs to get trending symbols
            # For now, we'll simulate by finding symbols with strong directional moves
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with strong trending characteristics (significant price changes)
            trending_symbols = []
            for symbol, ticker in tickers.items():
                if symbol.endswith('/USDT') and 'change' in ticker and ticker['change']:
                    # Look for symbols with strong directional movement (indicative of trending)
                    change_abs = abs(ticker['change'])
                    if change_abs > 3.0 and ticker['quoteVolume'] and ticker[
                        'quoteVolume'] > 1000000:  # 3%+ change and high volume
                        formatted_symbol = symbol.replace('/', '')
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                            trending_symbols.append(valid_symbol)
                        except ValueError:
                            continue  # Skip invalid symbols
                        if len(trending_symbols) >= 10:  # Limit to top 10 trending symbols
                            break

            return trending_symbols
        except Exception as e:
            self.logger.warning(f"Error in trend-oriented symbol discovery: {e}")
            return []  # Fall back to general discovery

    def _discover_volatility_oriented_symbols(self) -> List[str]:
        """Discover symbols with volatility opportunities for volatility watchers"""
        try:
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with high volatility (large differences between high/low)
            volatile_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                        'high' in ticker and ticker['high'] is not None and
                        'low' in ticker and ticker['low'] is not None and
                        'open' in ticker and ticker['open'] is not None and
                        'quoteVolume' in ticker and ticker['quoteVolume'] is not None):

                    if ticker['open'] != 0:
                        volatility = abs((ticker['high'] - ticker['low']) / ticker['open']) * 100
                        # Look for symbols with high volatility but also good volume
                        if volatility > 5.0 and ticker['quoteVolume'] > 500000:
                            formatted_symbol = symbol.replace('/', '')
                            try:
                                valid_symbol = Symbol(formatted_symbol)
                                volatile_symbols.append(valid_symbol)
                            except ValueError:
                                continue  # Skip invalid symbols
                            if len(volatile_symbols) >= 10:  # Limit to top 10 volatile symbols
                                break

            return volatile_symbols
        except Exception as e:
            self.logger.warning(f"Error in volatility-oriented symbol discovery: {e}")
            return []  # Fall back to general discovery

    def _discover_momentum_oriented_symbols(self) -> List[str]:
        """Discover symbols with momentum opportunities for market pulse watchers"""
        try:
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with strong momentum (recent significant price changes with volume)
            momentum_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                        'change' in ticker and ticker['change'] and
                        'quoteVolume' in ticker and ticker['quoteVolume']):
                    # Look for symbols with significant recent changes and high volume (momentum)
                    if abs(ticker['change']) > 2.5 and ticker['quoteVolume'] > 2000000:
                        formatted_symbol = symbol.replace('/', '')
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                            momentum_symbols.append(valid_symbol)
                        except ValueError:
                            continue  # Skip invalid symbols
                        if len(momentum_symbols) >= 10:  # Limit to top 10 momentum symbols
                            break

            return momentum_symbols
        except Exception as e:
            self.logger.warning(f"Error in momentum-oriented symbol discovery: {e}")
            return []  # Fall back to general discovery

    def _discover_anomaly_oriented_symbols(self) -> List[str]:
        """Discover symbols with unusual patterns for anomaly watchers"""
        try:
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with unusual characteristics (high volatility, low correlation with market, etc.)
            anomaly_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                        'change' in ticker and ticker['change'] and
                        'high' in ticker and 'low' in ticker and 'open' in ticker and
                        'quoteVolume' in ticker and ticker['quoteVolume']):

                    # Look for symbols with unusual patterns (high volatility + significant change)
                    change_abs = abs(ticker['change'])
                    volatility = abs((ticker['high'] - ticker['low']) / ticker['open']) * 100 if ticker[
                                                                                                     'open'] != 0 else 0

                    # Unusual = high volatility AND significant change (potential anomaly)
                    if change_abs > 4.0 and volatility > 6.0 and ticker['quoteVolume'] > 1000000:
                        formatted_symbol = symbol.replace('/', '')
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                            anomaly_symbols.append(valid_symbol)
                        except ValueError:
                            continue  # Skip invalid symbols
                        if len(anomaly_symbols) >= 10:  # Limit to top 10 anomaly symbols
                            break

            return anomaly_symbols
        except Exception as e:
            self.logger.warning(f"Error in anomaly-oriented symbol discovery: {e}")
            return []  # Fall back to general discovery

    def _discover_orderflow_oriented_symbols(self) -> List[str]:
        """Discover symbols with significant order flow for order flow watchers"""
        try:
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with high volume (indicative of significant order flow)
            high_volume_symbols = []
            for symbol, ticker in tickers.items():
                if symbol.endswith('/USDT') and 'quoteVolume' in ticker and ticker['quoteVolume']:
                    # Look for symbols with very high volume (indicative of significant order flow)
                    if ticker['quoteVolume'] > 50000000:  # Very high volume threshold
                        formatted_symbol = symbol.replace('/', '')
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                            high_volume_symbols.append(valid_symbol)
                        except ValueError:
                            continue  # Skip invalid symbols
                        if len(high_volume_symbols) >= 10:  # Limit to top 10 high-volume symbols
                            break

            return high_volume_symbols
        except Exception as e:
            self.logger.warning(f"Error in order flow-oriented symbol discovery: {e}")
            return []  # Fall back to general discovery

    def _discover_liquidity_oriented_symbols(self) -> List[str]:
        """Discover symbols with liquidity opportunities for liquidity watchers"""
        try:
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with high volume and tight spreads (good liquidity conditions)
            liquid_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                        'quoteVolume' in ticker and ticker['quoteVolume'] and
                        'high' in ticker and 'low' in ticker and ticker['high'] and ticker['low']):

                    # Look for symbols with high volume and relatively tight volatility (good liquidity)
                    if ticker['quoteVolume'] > 10000000 and ticker['high'] != 0:  # High volume
                        volatility = abs((ticker['high'] - ticker['low']) / ticker['high']) * 100
                        if volatility < 8.0:  # Not too volatile (better liquidity conditions)
                            formatted_symbol = symbol.replace('/', '')
                            try:
                                valid_symbol = Symbol(formatted_symbol)
                                liquid_symbols.append(valid_symbol)
                            except ValueError:
                                continue  # Skip invalid symbols
                            if len(liquid_symbols) >= 10:  # Limit to top 10 liquid symbols
                                break

            return liquid_symbols
        except Exception as e:
            self.logger.warning(f"Error in liquidity-oriented symbol discovery: {e}")
            return []  # Fall back to general discovery

    def _discover_funding_oriented_symbols(self) -> List[str]:
        """Discover symbols with significant funding rate opportunities for funding rate watchers"""
        try:
            import ccxt
            exchange = ccxt.binance()  # Use Binance as example, but this would connect to funding rate APIs

            # For funding rate discovery, we want perpetual futures with:
            # 1. High absolute funding rates (potential reversal opportunities)
            # 2. High funding rate acceleration (changing rapidly)

            # In a real implementation, this would connect to funding rate APIs
            # For now, we'll simulate by checking available perpetual symbols
            # Fetch available perpetual symbols
            markets = exchange.load_markets()
            perp_symbols = []

            for symbol, market in markets.items():
                if (symbol.endswith('USDT') and
                        market.get('swap', False) and  # Check if it's a swap/perpetual
                        market.get('active', True)):  # Check if active

                    # Add to perpetual symbols list
                    formatted_symbol = symbol.replace('/', '')
                    try:
                        valid_symbol = Symbol(formatted_symbol)
                        perp_symbols.append(valid_symbol)
                    except ValueError:
                        continue  # Skip invalid symbols

                    if len(perp_symbols) >= 20:  # Limit to top 20 perpetual symbols
                        break

            # For demonstration, return top perpetual symbols
            # In a real implementation, we'd filter based on current funding rate extremes
            return perp_symbols[:10]  # Return top 10 perpetual symbols

        except Exception as e:
            # If we can't get real perpetual data, fall back to general market cap discovery
            # but with preference for symbols that are likely to have perpetuals
            self.logger.warning(f"Using fallback for funding-oriented discovery: {e}")
            return self._discover_by_market_cap()


    def _discover_by_market_cap(self) -> List[str]:
        """Discover symbols based on market cap from CMC API."""
        try:
            import requests
            import os
            from dotenv import load_dotenv
            load_dotenv()

            cmc_api_key = os.getenv("CMC_API_KEY")
            cmc_listings_url = os.getenv("CMC_LISTINGS_URL",
                                         "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

            if not cmc_api_key:
                self.logger.warning("CMC_API_KEY not found, skipping market cap discovery")
                return []

            headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': cmc_api_key,
            }

            params = {
                'start': '1',
                'limit': '50',
                'convert': 'USD'
            }

            try:
                response = requests.get(cmc_listings_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                if 'data' in data:
                    # Extract symbols from the top coins with filtering
                    excluded_coins_str = os.getenv("CMC_EXCLUDED_COINS",
                                                   "BTC,ETH,SOL,ADA,DOT,XRP,DOGE,LINK,BNB,AVAX,MATIC,BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT,DOTUSDT,XRPUSDT,DOGEUSDT,LINKUSDT,BNBUSDT,AVAXUSDT,MATICUSDT")
                    excluded_coins = set(coin.strip().upper() for coin in excluded_coins_str.split(',') if coin.strip())

                    discovered_symbols = []
                    for coin in data['data']:
                        symbol = coin['symbol']
                        # Skip if in excluded list
                        if symbol in excluded_coins:
                            continue

                        # Format as proper trading pair
                        formatted_symbol = f"{symbol}USDT"

                        # Validate the symbol format
                        try:
                            valid_symbol = Symbol(formatted_symbol)  # This will validate the format
                            discovered_symbols.append(valid_symbol)
                            if len(discovered_symbols) >= 10:  # Limit to top 10 for auto-discovery
                                break
                        except ValueError:
                            continue  # Skip invalid symbols
                    return discovered_symbols
                else:
                    self.logger.warning("CMC API returned no data")
                    return []
            except Exception as e:
                self.logger.warning(f"Error fetching from CMC API: {e}")
                return []
        except Exception as e:
            self.logger.warning(f"Error during market cap symbol discovery: {e}")
            return []

    def _discover_by_price_activity(self) -> List[str]:
        """Discover symbols based on price/volume activity from exchange data."""
        try:
            # This would connect to exchange APIs to get recent activity
            # For now, we'll simulate using a placeholder that would connect to exchange data
            # This could use ccxt or other exchange APIs to get recent price/volume spikes
            discovered_symbols = self._get_active_symbols_from_exchange()

            if discovered_symbols:
                return discovered_symbols[:10]  # Limit to top 10

            # If exchange-based discovery fails, return empty list and let fallback happen
            return []
        except Exception as e:
            self.logger.warning(f"Error during activity-based symbol discovery: {e}")
            return []

    def _get_active_symbols_from_exchange(self) -> List[str]:
        """Get active symbols from exchange based on volume and price changes."""
        # In a real implementation, this would connect to exchange APIs
        # to get recent symbols with high volume or price volatility
        try:
            import ccxt
            # Use a public exchange to get top volume symbols
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Filter for USDT pairs and sort by volume
            usdt_pairs = {}
            for symbol, ticker in tickers.items():
                if symbol.endswith('/USDT') and 'quoteVolume' in ticker and ticker['quoteVolume']:
                    usdt_pairs[symbol] = ticker['quoteVolume']

            # Sort by volume and return top symbols
            sorted_symbols = sorted(usdt_pairs.items(), key=lambda x: x[1], reverse=True)
            top_symbols = []
            for pair, volume in sorted_symbols[:15]:  # Get top 15
                # Convert from exchange format to our format
                formatted = pair.replace('/', '').replace('USDT', 'USDT')  # Already in correct format
                if formatted.endswith('USDT'):
                    # Validate and convert to Symbol object
                    try:
                        valid_symbol = Symbol(formatted)
                        top_symbols.append(valid_symbol)
                    except ValueError:
                        continue  # Skip invalid symbols
                    if len(top_symbols) >= 10:  # Limit to 10
                        break

            return top_symbols
        except Exception as e:
            self.logger.warning(f"Error getting active symbols from exchange: {e}")
            return []

    def _discover_historical_candle_oriented_symbols(self) -> List[str]:
        """Discover symbols with reliable historical data for historical candle watchers."""
        try:
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with consistent historical data availability (high volume + consistent trading)
            historical_oriented_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                        'quoteVolume' in ticker and ticker['quoteVolume'] and
                        'count' in ticker and ticker['count'] and  # Number of trades (indicates data continuity)
                        'high' in ticker and ticker['high'] and
                        'low' in ticker and ticker['low']):

                    # Look for symbols with good liquidity and consistent trading for reliable historical data
                    volume = ticker['quoteVolume']
                    trade_count = ticker['count']

                    # High volume and consistent trading indicates reliable historical data
                    if volume > 5000000 and trade_count > 2000:  # Good volume and consistent trading
                        formatted_symbol = symbol.replace('/', '')  # Convert BTC/USDT to BTCUSDT
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                            historical_oriented_symbols.append(valid_symbol)
                        except ValueError:
                            continue  # Skip invalid symbols

                        if len(historical_oriented_symbols) >= 10:  # Limit to top 10 symbols
                            break

            # If we don't have enough symbols, fall back to major coins with high volume
            if len(historical_oriented_symbols) < 5:
                major_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
                                 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT']
                historical_oriented_symbols = major_symbols

            return historical_oriented_symbols
        except Exception as e:
            self.logger.warning(f"Error in historical candle-oriented symbol discovery: {e}")
            # Fall back to general discovery if specific discovery fails
            return self._discover_by_market_cap()

    def _discover_tick_oriented_symbols(self) -> List[str]:
        """Discover symbols with high tick frequency and trading activity for tick watchers."""
        try:
            import ccxt
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with high tick frequency (high volume + high number of trades)
            tick_oriented_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                        'quoteVolume' in ticker and ticker['quoteVolume'] and
                        'count' in ticker and ticker['count']):  # 'count' represents number of trades

                    # High volume indicates frequent trading
                    volume = ticker['quoteVolume']

                    # High trade count indicates frequent ticks
                    trade_count = ticker['count']

                    # Look for symbols with both high volume and high trade frequency
                    if volume > 10000000 and trade_count > 5000:  # High volume and frequent trades
                        formatted_symbol = symbol.replace('/', '')  # Convert BTC/USDT to BTCUSDT
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                            tick_oriented_symbols.append(valid_symbol)
                        except ValueError:
                            continue  # Skip invalid symbols

                        if len(tick_oriented_symbols) >= 10:  # Limit to top 10 tick-active symbols
                            break

            # If we don't have enough symbols with trade count data, fall back to high-volume symbols
            if len(tick_oriented_symbols) < 5:
                high_volume_symbols = []
                for symbol, ticker in tickers.items():
                    if (symbol.endswith('/USDT') and
                            'quoteVolume' in ticker and ticker['quoteVolume'] and
                            ticker['quoteVolume'] > 20000000):  # Even higher volume threshold
                        formatted_symbol = symbol.replace('/', '')
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                            high_volume_symbols.append(valid_symbol)
                        except ValueError:
                            continue  # Skip invalid symbols

                        if len(high_volume_symbols) >= 10:
                            break

                tick_oriented_symbols = high_volume_symbols

            return tick_oriented_symbols
        except Exception as e:
            self.logger.warning(f"Error in tick-oriented symbol discovery: {e}")
            # Fall back to general discovery if tick-specific discovery fails
            return self._discover_by_market_cap()

    def _discover_by_trending_searches(self) -> List[str]:
        """Discover symbols based on trending searches or social media activity."""
        # This could integrate with social media APIs or other trending indicators
        # For now, this is a placeholder that would implement such functionality
        try:
            # In a real implementation:
            # - Monitor social media for crypto mentions
            # - Track Google Trends for crypto searches
            # - Monitor crypto news sentiment
            # - Track sudden increases in trading volume across exchanges
            discovered_symbols = []
            return discovered_symbols
        except Exception as e:
            self.logger.warning(f"Error during trending-based symbol discovery: {e}")
            return []

    def _update_symbol_list(self):
        """Dynamically update the list of symbols to monitor based on market conditions."""
        if not self.auto_discover_symbols:
            return  # Only update if auto-discovery is enabled

        # Use time-based rotation for more dynamic updates
        current_symbols = [s.value for s in self.symbols]
        new_symbols = self._discover_by_time_based_rotation()
        new_symbol_values = [s.value for s in new_symbols]

        if current_symbols != new_symbol_values:
            self.logger.info(f"🔄 Symbol list updated: {current_symbols} -> {new_symbol_values}")
            # Here we would need to reinitialize watchers for new symbols
            removed_symbols = set(current_symbols) - set(new_symbol_values)
            added_symbols = set(new_symbol_values) - set(current_symbols)

            # Remove watchers for symbols no longer in the list
            for symbol_str in removed_symbols:
                if symbol_str in self.watchers:
                    # Stop all watchers for this symbol
                    for watcher_name, watcher in self.watchers[symbol_str].items():
                        if hasattr(watcher, 'stop'):
                            watcher.stop()
                    del self.watchers[symbol_str]
                    # Remove from symbols list
                    self.symbols = [s for s in self.symbols if s.value != symbol_str]

                # Also check if Symbol object exists in symbols list
                symbol_obj_to_remove = None
                for s in self.symbols:
                    if s.value == symbol_str:
                        symbol_obj_to_remove = s
                        break
                if symbol_obj_to_remove:
                    self.symbols.remove(symbol_obj_to_remove)

            # Add watchers for new symbols
            for symbol_str in added_symbols:
                symbol = Symbol(symbol_str)
                if symbol not in self.symbols:  # Avoid duplicates
                    self.symbols.append(symbol)
                    # Initialize watchers for the new symbol
                    symbol_watchers = {}

                    # Check each watcher type before creating to avoid unnecessary instantiation
                    if os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
                        # Use the shared broker service instead of creating new ones
                        target_broker = os.getenv('TARGET_BROKER_MARKET_PULSE', 'binance')  # Default to binance
                        symbol_watchers['market_pulse'] = MarketPulseWatcher("MarketPulse", symbol.value, broker_service=self.broker_service, target_broker=target_broker)

                    if os.getenv('VOLATILITY_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.volatility import VolatilityWatcher
                        # Use the shared broker service instead of creating new ones
                        target_broker = os.getenv('TARGET_BROKER_VOLATILITY', 'binance')  # Default to binance
                        symbol_watchers['volatility'] = VolatilityWatcher("Volatility", symbol.value, broker_service=self.broker_service, target_broker=target_broker)

                    if os.getenv('TREND_MTF_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
                        # Use the shared broker service instead of creating new ones
                        target_broker = os.getenv('TARGET_BROKER_TREND_MTF', 'binance')  # Default to binance
                        symbol_watchers['trend_mtf'] = TrendMTFWatcher("TrendMTF", symbol.value, broker_service=self.broker_service, target_broker=target_broker)

                    if os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
                        # Use the shared broker service instead of creating new ones
                        target_broker = os.getenv('TARGET_BROKER_ANOMALY_ML', 'binance')  # Default to binance
                        symbol_watchers['anomaly_ml'] = AnomalyMLWatcher("AnomalyML", symbol.value, broker_service=self.broker_service, target_broker=target_broker)

                    if os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
                        # Use the shared broker service instead of creating new ones
                        target_broker = os.getenv('TARGET_BROKER_ORDERFLOW_WS', 'binance')  # Default to binance
                        symbol_watchers['orderflow_ws'] = OrderFlowWSWatcher("OrderFlowWS", symbol.value, broker_service=self.broker_service, target_broker=target_broker)

                    if os.getenv('CMC_SCREENER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.cmc_screener import CMCScreener
                        symbol_watchers['cmc_screener'] = CMCScreener(name=f"CMCWatcher_{symbol.value}", symbol=symbol.value)

                    if os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
                        # Use the shared broker service instead of creating new ones
                        target_broker = os.getenv('TARGET_BROKER_FUNDING_RATE', 'binance')  # Default to binance
                        symbol_watchers['funding_rate'] = FundingRateWatcher("FundingRate", symbol.value, broker_service=self.broker_service, target_broker=target_broker)

                    if os.getenv('LIQUIDITY_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.liquidity import LiquidityWatcher
                        # Use the shared broker service instead of creating new ones
                        target_broker = os.getenv('TARGET_BROKER_LIQUIDITY', 'binance')  # Default to binance
                        symbol_watchers['liquidity'] = LiquidityWatcher("Liquidity", symbol.value, broker_service=self.broker_service, target_broker=target_broker)

                    if os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter
                        # Use the shared broker service instead of creating new ones
                        # Note: This adapter doesn't accept target_broker parameter
                        symbol_watchers['historical_candle'] = HistoricalCandleWatcherAdapter("HistoricalCandle", symbol.value, broker_service=self.broker_service)

                    if os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true':
                        from infrastructure.watchers.adapters.tick import TickWatcherAdapter
                        # Use the shared broker service instead of creating new ones
                        # Note: This adapter doesn't accept target_broker parameter
                        symbol_watchers['tick_watcher'] = TickWatcherAdapter("TickWatcher", symbol.value, broker_service=self.broker_service)

                    self.watchers[symbol.value] = symbol_watchers
                    # Start new watchers
                    for watcher_name, watcher in self.watchers[symbol.value].items():
                        if hasattr(watcher, 'start'):
                            watcher.start()

            # Update symbol list to match the new discovery
            self.symbols = new_symbols
        else:
            self.logger.debug(f"✅ Symbol list unchanged: {len(current_symbols)} symbols")

    def start_periodic_symbol_updates(self, update_interval_minutes=30):
        """Start a background thread to periodically update symbols."""
        import threading
        import time

        def update_loop():
            while self.is_running:
                try:
                    self._update_symbol_list()
                    # Sleep for the specified interval
                    for _ in range(update_interval_minutes * 60):  # Convert minutes to seconds
                        if not self.is_running:  # Check if we should stop
                            break
                        time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Error in periodic symbol update: {e}")
                    time.sleep(60)  # Wait a minute before retrying

        # Start the update thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        self.logger.info(f"🔄 Started periodic symbol updates every {update_interval_minutes} minutes")

    def _discover_by_recent_activity(self) -> List[Symbol]:
        """Discover symbols based on recent market activity like volume surges or price movements."""
        try:
            # This method focuses on recent market activity rather than just market cap
            import ccxt
            import time
            import random

            exchange = ccxt.binance()

            # Get recent tickers
            tickers = exchange.fetch_tickers()

            # Filter for active USDT pairs with recent volume and price changes
            active_symbols = []
            for symbol, ticker in tickers.items():
                if not symbol.endswith('/USDT'):
                    continue

                # Check if the ticker has recent data
                if not all(
                        key in ticker for key in ['close', 'high', 'low', 'quoteVolume', 'change', 'changePercentage']):
                    continue

                # Look for symbols with high volume and price movement
                volume = ticker['quoteVolume'] or 0
                price_change_pct = abs(ticker['changePercentage'] or 0)

                # Thresholds for "active" symbols (these values can be tuned)
                min_volume_threshold = 10_000_000  # $10M in volume
                min_change_threshold = 2.0  # 2% price movement

                if volume > min_volume_threshold or price_change_pct > min_change_threshold:
                    formatted_symbol = symbol.replace('/', '')  # Convert BTC/USDT to BTCUSDT
                    active_symbols.append({
                        'symbol': Symbol(formatted_symbol),
                        'volume': volume,
                        'change_pct': price_change_pct,
                        'close': ticker['close']
                    })

            # Sort by a combination of volume and price movement for relevance
            active_symbols.sort(key=lambda x: x['volume'] * (1 + x['change_pct'] / 100), reverse=True)

            # Return top symbols, but ensure we include some stable major coins too
            top_active = [item['symbol'] for item in active_symbols[:7]]  # Top 7 active symbols

            # Add some major coins that might not be trending but are important
            major_coins = [Symbol('BTCUSDT'), Symbol('ETHUSDT')]
            important_symbols = [coin for coin in major_coins if
                                 coin not in [item['symbol'] for item in active_symbols]]

            # Combine and limit to 10
            final_symbols = (top_active + important_symbols)[:10]

            self.logger.info(f"📈 Found {len(final_symbols)} active symbols based on recent activity")
            return final_symbols

        except Exception as e:
            self.logger.warning(f"Error during recent activity symbol discovery: {e}")
            # Fallback to basic discovery if activity detection fails
            # But ensure we return Symbol objects, not strings
            basic_symbols = self._discover_by_market_cap()  # Use direct method to avoid mixed types
            symbol_objects = []
            for symbol_str in basic_symbols:
                try:
                    symbol_objects.append(Symbol(symbol_str))
                except ValueError:
                    continue  # Skip invalid symbols
            return symbol_objects

    def _discover_by_random_top_volume(self) -> List[Symbol]:
        """Discover symbols by randomly selecting from top volume coins to add variety."""
        try:
            import ccxt
            import random

            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Get USDT pairs with high volume
            high_volume_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                    'quoteVolume' in ticker and ticker['quoteVolume'] and
                    ticker['quoteVolume'] > 5_000_000):  # At least $5M in volume
                    formatted_symbol = symbol.replace('/', '')  # Convert BTC/USDT to BTCUSDT
                    # Validate the symbol format before adding
                    try:
                        valid_symbol = Symbol(formatted_symbol)
                        high_volume_symbols.append(valid_symbol)
                    except ValueError:
                        # Skip invalid symbols
                        continue

            # Randomly shuffle and take top 10 to add variety
            random.shuffle(high_volume_symbols)
            selected_symbols = high_volume_symbols[:10]

            self.logger.info(f"🎲 Randomly selected {len(selected_symbols)} high-volume symbols for variety")
            return selected_symbols

        except Exception as e:
            self.logger.warning(f"Error during random volume symbol discovery: {e}")
            # Convert to Symbol objects to maintain consistency
            market_cap_symbols = self._discover_by_market_cap()
            symbol_objects = []
            for symbol_str in market_cap_symbols:
                try:
                    symbol_objects.append(Symbol(symbol_str))
                except ValueError:
                    continue  # Skip invalid symbols
            return symbol_objects

    def _discover_by_new_and_emerging(self) -> List[Symbol]:
        """Discover newer or emerging coins that might not be in top market cap but showing activity."""
        try:
            import ccxt
            import requests
            import os
            from dotenv import load_dotenv
            load_dotenv()

            # First, try to get trending coins from CMC (if API supports it)
            cmc_api_key = os.getenv("CMC_API_KEY")
            if cmc_api_key:
                # Try to get trending coins from CMC
                headers = {
                    'Accepts': 'application/json',
                    'X-CMC_PRO_API_KEY': cmc_api_key,
                }

                # Get trending coins (this endpoint might not exist in free tier)
                trending_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/trending/latest"
                try:
                    response = requests.get(trending_url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data:
                            trending_symbols = []
                            for coin in data['data'][:10]:  # Top 10 trending
                                symbol = coin['symbol']
                                formatted_symbol = f"{symbol}USDT"
                                try:
                                    Symbol(formatted_symbol)
                                    trending_symbols.append(Symbol(formatted_symbol))
                                except ValueError:
                                    continue
                            if trending_symbols:
                                self.logger.info(f"🔥 Found {len(trending_symbols)} trending symbols")
                                return trending_symbols
                except:
                    pass  # CMC trending endpoint might not be available

            # Fallback: Use exchange data to find coins with increasing volume
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Look for coins with significant volume increases compared to their historical average
            # For now, we'll focus on coins that are not in the top market cap but have good activity
            active_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                    'quoteVolume' in ticker and ticker['quoteVolume'] and
                    'changePercentage' in ticker and ticker['changePercentage'] is not None):

                    volume = ticker['quoteVolume']
                    change_pct = abs(ticker['changePercentage'])

                    # Look for coins with moderate volume but high percentage changes
                    # This often indicates newer/emerging coins gaining attention
                    if volume > 1_000_000 and change_pct > 5.0:  # $1M+ volume and 5%+ change
                        formatted_symbol = symbol.replace('/', '')

                        # Validate the symbol format before adding
                        try:
                            valid_symbol = Symbol(formatted_symbol)
                        except ValueError:
                            # Skip invalid symbols
                            continue

                        # Exclude major coins to focus on emerging ones
                        major_exclusions = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 'AVAX', 'MATIC', 'LINK']
                        base_symbol = formatted_symbol.replace('USDT', '')
                        if base_symbol not in major_exclusions:
                            active_symbols.append({
                                'symbol': valid_symbol,
                                'volume': volume,
                                'change_pct': change_pct
                            })

            # Sort by change percentage to prioritize emerging coins
            active_symbols.sort(key=lambda x: x['change_pct'], reverse=True)

            # Take top emerging coins
            emerging_symbols = [item['symbol'] for item in active_symbols[:8]]

            # Add some major coins to maintain balance
            major_alternatives = [Symbol('SOLUSDT'), Symbol('XRPUSDT'), Symbol('ADAUSDT'), Symbol('AVAXUSDT')]
            selected_symbols = emerging_symbols[:6] + major_alternatives[:4]

            # Shuffle to add some randomness
            import random
            random.shuffle(selected_symbols)

            self.logger.info(f"🚀 Found {len(emerging_symbols)} emerging symbols, returning {len(selected_symbols)} balanced selection")
            return selected_symbols[:10]

        except Exception as e:
            self.logger.warning(f"Error during new/emerging symbol discovery: {e}")
            # Fallback to market cap discovery but with some randomization
            market_cap_symbols = self._discover_by_market_cap()
            # Convert to Symbol objects and add some randomization by shuffling and taking a subset
            symbol_objects = []
            for symbol_str in market_cap_symbols:
                try:
                    symbol_objects.append(Symbol(symbol_str))
                except ValueError:
                    continue  # Skip invalid symbols
            import random
            random.shuffle(symbol_objects)
            return symbol_objects[:10]

    def _discover_by_time_based_rotation(self) -> List[Symbol]:
        """Rotate discovery methods based on time to provide variety."""
        import time

        # Use current time to determine which discovery method to use
        current_hour = time.localtime().tm_hour
        current_minute = time.localtime().tm_min

        # Rotate through different discovery methods based on time
        # Changed from every 10 minutes to every 2 hours to reduce excessive updates
        method_index = (current_hour // 2) % 4  # Every 2 hours, rotate method

        if method_index == 0:
            self.logger.info("🕐 Using market cap based discovery")
            return self._discover_by_market_cap()
        elif method_index == 1:
            self.logger.info("🕐 Using recent activity based discovery")
            return self._discover_by_recent_activity()
        elif method_index == 2:
            self.logger.info("🕐 Using random volume based discovery")
            return self._discover_by_random_top_volume()
        else:
            self.logger.info("🕐 Using new/emerging coins discovery")
            return self._discover_by_new_and_emerging()

    def _initialize_watchers(self):
        """Initialize watcher adapters for each symbol using the watcher initialization service."""
        # Use the watcher initialization service to handle the complex initialization logic
        self.watchers, self.broker_service = self.watcher_init_service.initialize_watchers(
            self.symbols,
            getattr(self, '_watcher_specific_symbols', None)
        )
        
        # Set the watchers and symbols in the monitoring service
        self.monitoring_service.set_watchers_and_symbols(self.watchers, self.symbols)

    def start_monitoring(self):
        """Start continuous market monitoring."""
        # Delegate to the monitoring service
        self.monitoring_service.start_monitoring()

    def stop_monitoring(self):
        """Stop market monitoring."""
        # Delegate to the monitoring service
        self.monitoring_service.stop_monitoring()

    def _monitoring_loop(self):
        """Main monitoring loop that continuously checks for opportunities."""
        self.logger.info("🔄 Market opportunity monitoring loop started")

        # Track statistics for periodic reporting
        last_report_time = time.time()
        report_interval = 60  # seconds between detailed reports
        analysis_count = 0
        signals_found = 0

        # Track symbol-specific analytics to ensure balanced processing
        symbol_analysis_count = {symbol.value: 0 for symbol in self.symbols}
        symbol_signal_count = {symbol.value: 0 for symbol in self.symbols}

        while self.is_running:
            try:
                opportunities = self._check_market_opportunities()
                analysis_count += len(self.symbols)

                # Update symbol-specific counts
                for symbol in self.symbols:
                    symbol_analysis_count[symbol.value] += 1

                # Count signals found and track which symbols generated them
                for opportunity in opportunities:
                    if opportunity.get('recommendation') and opportunity['confidence'] > 0.6:
                        signals_found += 1
                        # Track which symbol generated the signal
                        symbol_val = opportunity.get('symbol')
                        if symbol_val and symbol_val in symbol_signal_count:
                            symbol_signal_count[symbol_val] += 1

                # Log periodic detailed reports
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    # Create a summary of signal distribution across symbols
                    active_symbols = {sym: cnt for sym, cnt in symbol_signal_count.items() if cnt > 0}

                    self.logger.info(
                        f"📊 WATCHER ANALYTICS: Analyzed {analysis_count} symbol checks in last {report_interval}s | "
                        f"Signals found: {signals_found} | Monitored symbols: {len(self.symbols)}")

                    if active_symbols:
                        self.logger.info(f"📈 SIGNAL DISTRIBUTION: {active_symbols}")

                    # Log analysis distribution to ensure all symbols are being processed
                    analysis_distribution = {sym: cnt for sym, cnt in symbol_analysis_count.items() if cnt > 0}
                    if analysis_distribution:
                        self.logger.debug(f"🔍 ANALYSIS DISTRIBUTION: {analysis_distribution}")

                    analysis_count = 0
                    signals_found = 0
                    last_report_time = current_time

                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Continue monitoring even if there's an error

    def _check_market_opportunities(self):
        """Check each symbol for trading opportunities."""
        all_opportunities = []

        # First, fetch market data and update all watchers with fresh data
        for symbol in self.symbols:
            self._update_watchers_with_market_data(symbol)
            # Add a small delay to ensure data is processed by watchers
            import time
            time.sleep(0.1)  # Small delay to allow data processing

        # Then analyze each symbol with a time limit to ensure fair processing
        total_start_time = time.time()

        # Process symbols in their original order to ensure systematic processing
        for symbol in self.symbols:
            # Add logging to track which symbol is being processed
            self.logger.debug(f"🔍 Processing symbol: {symbol.value}")

            start_time = time.time()
            opportunities = self._analyze_symbol(symbol)

            # Log processing time for this symbol
            processing_time = time.time() - start_time
            self.logger.debug(f"⏱️ Symbol {symbol.value} processed in {processing_time:.2f}s")

            if opportunities:
                self._process_opportunities(symbol, opportunities)
                all_opportunities.append(opportunities)

        # Log the total processing time for all symbols
        total_processing_time = time.time() - total_start_time
        self.logger.info(f"📊 Total processing for {len(self.symbols)} symbols completed in {total_processing_time:.2f}s")

        return all_opportunities

    def _update_watchers_with_market_data(self, symbol: Symbol):
        """Fetch market data and update all watchers for this symbol."""
        if not self.market_data_repo:
            self.logger.warning(f"No market data repository available for {symbol.value}")
            return

        # Check if symbol is available on exchange before processing
        if hasattr(self.market_data_repo, 'is_symbol_available'):
            if not self.market_data_repo.is_symbol_available(symbol.value):
                self.logger.debug(f"Skipping unavailable symbol: {symbol.value}")
                return

        try:
            # Fetch latest market data for the symbol
            # The market_data_repo should have a method to fetch data
            # This is a generic approach that should work with different data providers
            market_data = None

            # Try different possible methods to fetch data
            if hasattr(self.market_data_repo, 'get_historical_data'):
                # Get historical data for initializing watchers with sufficient history
                try:
                    historical_data = self.market_data_repo.get_historical_data(symbol=Symbol(symbol.value), period="30m", timeframe="1m")
                    if historical_data:
                        # Use the most recent data point to initialize, but the historical data will help populate history
                        market_data = historical_data[0] if historical_data else None
                        # Initialize watcher histories with historical data
                        self._initialize_watcher_histories_with_historical_data(symbol, historical_data)
                    else:
                        # Fallback to current price if no historical data
                        market_data = None
                        # Try to get current price as fallback
                        if hasattr(self.market_data_repo, 'get_current_price'):
                            price = self.market_data_repo.get_current_price(Symbol(symbol.value))
                            market_data = {'price': price, 'timestamp': datetime.now().timestamp(), 'symbol': symbol.value}
                except Exception as e:
                    # If get_historical_data fails, try current price as fallback
                    if hasattr(self.market_data_repo, 'get_current_price'):
                        price = self.market_data_repo.get_current_price(Symbol(symbol.value))
                        market_data = {'price': price, 'timestamp': datetime.now().timestamp(), 'symbol': symbol.value}
                    else:
                        market_data = None
            elif hasattr(self.market_data_repo, 'get_latest_data'):
                market_data = self.market_data_repo.get_latest_data(symbol.value)
            elif hasattr(self.market_data_repo, 'fetch_market_data'):
                market_data = self.market_data_repo.fetch_market_data(symbol.value)
            elif hasattr(self.market_data_repo, 'get_market_data'):
                market_data = self.market_data_repo.get_market_data(symbol.value)
            elif hasattr(self.market_data_repo, 'get_current_price'):
                # For mock data provider, get current price
                price = self.market_data_repo.get_current_price(Symbol(symbol.value))
                market_data = {'price': price, 'timestamp': datetime.now().timestamp(), 'symbol': symbol.value}
            elif hasattr(self.market_data_repo, 'get_data'):
                market_data = self.market_data_repo.get_data(symbol.value)
            else:
                # If no standard method exists, try to use it as a callable
                try:
                    market_data = self.market_data_repo(symbol.value)
                except:
                    self.logger.warning(f"Unable to fetch market data for {symbol.value} - no compatible method found")
                    return

            if market_data is None:
                self.logger.warning(f"No market data returned for {symbol.value}")
                return

            # Update all watchers for this symbol with the market data
            symbol_str = symbol.value
            if symbol_str in self.watchers:
                for watcher_name, watcher in self.watchers[symbol_str].items():
                    try:
                        # Convert market_data to the format expected by the watcher's update_data method
                        # The watchers expect a dictionary with market data

                        # Different watchers expect different data formats
                        # HistoricalCandleWatcher expects data in the format: {'candle': {...}}
                        # Other watchers might expect flat format
                        if 'historical' in watcher_name.lower():
                            # Format for historical candle watchers
                            candle_data = {
                                'open': market_data.get('open', market_data.get('price', market_data.get('close', 0))),
                                'high': market_data.get('high', market_data.get('price', market_data.get('close', 0))),
                                'low': market_data.get('low', market_data.get('price', market_data.get('close', 0))),
                                'close': market_data.get('close', market_data.get('price', market_data.get('last', 0))),
                                'volume': market_data.get('volume', market_data.get('quoteVolume', 0)),
                                'timestamp': market_data.get('timestamp', datetime.now().timestamp())
                            }
                            formatted_data = {'candle': candle_data}
                        else:
                            # Use the standard format for other watchers
                            formatted_data = self._format_market_data_for_watcher(market_data)

                        watcher.update_data(formatted_data)
                    except Exception as e:
                        self.logger.warning(f"Error updating watcher {watcher_name} with market data: {e}")

        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol.value}: {e}")

    def _format_market_data_for_watcher(self, market_data):
        """Format market data to the structure expected by watchers."""
        # The format depends on the data source, but typically includes:
        # price, volume, high, low, open, close, timestamp
        formatted_data = {}

        if isinstance(market_data, dict):
            # If it's already a dictionary, extract common fields
            formatted_data.update({
                'close': market_data.get('close') or market_data.get('price') or market_data.get('last'),
                'open': market_data.get('open'),
                'high': market_data.get('high'),
                'low': market_data.get('low'),
                'volume': market_data.get('volume') or market_data.get('quoteVolume'),
                'timestamp': market_data.get('timestamp'),
                'bid': market_data.get('bid'),
                'ask': market_data.get('ask'),
            })
        elif hasattr(market_data, '__dict__'):
            # If it's an object, try to extract attributes
            data_dict = market_data.__dict__
            formatted_data.update({
                'close': data_dict.get('close') or data_dict.get('price') or data_dict.get('last'),
                'open': data_dict.get('open'),
                'high': data_dict.get('high'),
                'low': data_dict.get('low'),
                'volume': data_dict.get('volume') or data_dict.get('quoteVolume'),
                'timestamp': data_dict.get('timestamp'),
                'bid': data_dict.get('bid'),
                'ask': data_dict.get('ask'),
            })
        else:
            # If it's a single value, assume it's a price
            formatted_data['close'] = market_data

        # Remove None values
        formatted_data = {k: v for k, v in formatted_data.items() if v is not None}
        return formatted_data

    def _initialize_watcher_histories_with_historical_data(self, symbol: Symbol, historical_data: List[Dict[str, Any]]):
        """Initialize watcher histories with historical data to enable immediate signal generation."""
        symbol_str = symbol.value
        if symbol_str not in self.watchers:
            return

        # Update each watcher with all historical data points to build up their history
        for data_point in historical_data:
            for watcher_name, watcher in self.watchers[symbol_str].items():
                try:
                    formatted_data = self._format_market_data_for_watcher(data_point)
                    watcher.update_data(formatted_data)
                except Exception as e:
                    self.logger.warning(f"Error updating watcher {watcher_name} with historical data point: {e}")

    def _analyze_symbol(self, symbol: Symbol) -> Dict[str, Any]:
        """Analyze a symbol using all available watchers - only if enabled.
        Implements correct architecture: Watcher → Engine → Fusion → Strategy → Broker"""
        symbol_str = symbol.value

        # Validate symbol against approved list before processing
        if not symbol_validator.is_symbol_approved(symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Skipping processing.")
            return {
                'symbol': symbol_str,
                'timestamp': datetime.now(),
                'observations': {},
                'indicators': {},
                'recommendation': None,
                'confidence': 0.0,
                'strategy_suggestion': 'SKIPPED',  # Mark as skipped due to validation
                'execution_intent': None
            }

        # Log that the symbol analysis is starting
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            self.logger.log_background_activity(
                "Symbol Analysis",
                f"Starting analysis for {symbol_str}",
                symbol=symbol_str
            )

        opportunities = {
            'symbol': symbol_str,
            'timestamp': datetime.now(),
            'observations': {},
            'indicators': {},
            'recommendation': None,
            'confidence': 0.0,
            'strategy_suggestion': 'PENDING',  # Strategy selection happens in Strategy layer
            'execution_intent': None
        }

        # Get priority order for watchers based on their predictive power
        # This allows us to implement early exit logic if initial key indicators show no opportunity
        watcher_priority_order = self._get_watcher_priority_order()

        # Process each watcher individually - only emit raw market observations
        for watcher_name in watcher_priority_order:
            # Check if this watcher exists for this symbol
            if watcher_name not in self.watchers[symbol_str]:
                continue

            watcher = self.watchers[symbol_str][watcher_name]

            # Log that we're starting to analyze with this watcher
            if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                self.logger.log_background_activity(
                    "Watcher Analysis",
                    f"Analyzing {symbol_str} with {watcher_name}",
                    symbol=symbol_str,
                    watcher=watcher_name
                )

            # Check if the specific watcher has an enabled attribute and if it's enabled
            watcher_is_enabled = True  # Default assumption

            # Check if the watcher has an enabled attribute
            if hasattr(watcher, 'enabled'):
                watcher_is_enabled = watcher.enabled

            # Only call analyze if the watcher is enabled
            if watcher_is_enabled:
                try:
                    # Step 1: Watcher generates raw market observation (no strategy selection)
                    observation = watcher.analyze(symbol)

                    # Log the complete flow for this watcher regardless of whether it generated an observation
                    if observation:
                        # Store raw observation from watcher
                        raw_observation_data = {
                            'observation_type': observation.observation_type,
                            'observation_value': observation.observation_value,
                            'confidence': float(observation.confidence.value) if hasattr(observation.confidence,
                                                                                        'value') else float(
                                observation.confidence),
                            'timestamp': observation.timestamp.isoformat() if hasattr(observation,
                                                                                     'timestamp') else datetime.now().isoformat(),
                            'metadata': observation.metadata if hasattr(observation, 'metadata') else {},
                            'watcher_name': watcher_name
                        }
                        opportunities['observations'][watcher_name] = raw_observation_data

                        # Log the individual watcher observation
                        self.logger.log_watcher_analysis(
                            watcher=watcher_name,
                            symbol=symbol_str,
                            result=f"Observation Generated: {observation.observation_type}",
                            confidence=float(observation.confidence.value) if hasattr(observation.confidence, 'value') else float(
                                observation.confidence),
                            signal_type=observation.observation_type
                        )

                        # Emit the raw market observation to the event system for proper processing
                        if self.event_router:
                            try:
                                from shared.event_system import EventType
                                self.event_router.publish_observation(
                                    observation=observation,
                                    source=f"Watcher_{watcher_name}",
                                    correlation_id=f"{symbol_str}_{datetime.now().timestamp()}"
                                )
                                self.logger.info(f"Emitting market observation to event system: {observation.observation_type} for {symbol_str}")
                            except Exception as e:
                                self.logger.error(f"Error emitting observation to event system: {e}")
                        else:
                            self.logger.warning("No event router available to emit observation")

                        # Implement early exit logic: if this is an early watcher and it indicates no opportunity,
                        # we might want to skip remaining watchers for efficiency
                        if self._should_skip_remaining_watchers(observation, watcher_name):
                            self.logger.info(f"Early exit triggered for {symbol_str} after {watcher_name} - no profitable opportunity detected")
                            break

                    else:
                        # No observation was generated by the watcher
                        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                            self.logger.log_background_activity(
                                "Observation Analysis",
                                f"No observation generated by {watcher_name} for {symbol_str}",
                                symbol=symbol_str,
                                watcher=watcher_name
                            )

                        # Log that the watcher didn't generate an observation
                        self.logger.log_watcher_analysis(
                            watcher=watcher_name,
                            symbol=symbol_str,
                            result="No Observation Generated"
                        )

                except Exception as e:
                    self.logger.error(f"Error analyzing {symbol_str} with {watcher_name}: {e}")
                    # Log the error in watcher analysis (don't show confidence for errors)
                    self.logger.log_watcher_analysis(
                        watcher=watcher_name,
                        symbol=symbol_str,
                        result=f"Error: {str(e)}"
                        # Don't pass confidence when there's an error
                    )
                    continue

        # Log the final analysis result for this symbol with complete flow tracking
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            if opportunities['recommendation']:
                self.logger.log_background_activity(
                    "Symbol Analysis Complete",
                    f"Opportunity found for {symbol_str}: {opportunities['recommendation']} with confidence {opportunities['confidence']:.2%}",
                    symbol=symbol_str,
                    recommendation=opportunities['recommendation'],
                    confidence=opportunities['confidence']
                )
            else:
                self.logger.log_background_activity(
                    "Symbol Analysis Complete",
                    f"No opportunities found for {symbol_str}",
                    symbol=symbol_str
                )

        return opportunities

    def _get_watcher_priority_order(self) -> List[str]:
        """Get the priority order for watchers based on their predictive power."""
        # Define priority order - most predictive watchers first
        # This allows for early exit if initial key indicators show no opportunity
        priority_order = [
            'market_pulse',      # Market pulse often indicates immediate opportunities
            'trend_mtf',         # Multi-timeframe trend is fundamental
            'volatility',        # Volatility can indicate trade viability
            'anomaly_ml',        # ML anomalies can be predictive
            'liquidity',         # Liquidity affects trade execution
            'funding_rate',      # Funding rates affect perpetual positions
            'cmc_screener',      # General market conditions
            'orderflow_ws',      # Order flow for execution timing
            'historical_candle', # Historical patterns
            'tick_watcher'       # Tick-level analysis (usually confirmatory)
        ]

        return priority_order

    def _should_skip_remaining_watchers(self, observation, watcher_name: str) -> bool:
        """Determine if remaining watchers should be skipped based on early indicators."""
        # DISABLED: Never skip remaining watchers to ensure all observations flow through the system
        # The architectural flow should be: Watcher → Engine → Fusion → Strategy → Broker
        # Watchers should only emit observations, not make trading decisions
        return False  # Always return False to ensure all watchers run

    def _process_opportunities(self, symbol: Symbol, opportunities: Dict[str, Any]):
        """Process detected opportunities - but in the correct architecture,
        the watcher should only emit observations and not handle callbacks directly."""

        # The watcher should only emit raw market observations to the event system
        # The actual processing should happen through the event-driven flow

        # Log that we're processing opportunities
        if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
            self.logger.log_background_activity(
                "Opportunity Processing",
                f"Processing opportunities for {symbol.value}",
                symbol=symbol.value
            )

    def _execute_intent_trade(self, execution_intent):
        """This method should not exist in the Watcher layer.
        The Watcher should only emit market observations, never execute trades directly.
        This is a violation of the architectural pattern: Watcher → Engine → Fusion → Strategy → Broker.
        The execution should happen only in the Broker layer after going through all intermediate layers."""

        # Log an error that this method is being called, which indicates an architectural violation
        self.logger.error(
            f"❌ ARCHITECTURE VIOLATION: Watcher layer attempted to execute trade directly for {execution_intent.symbol.value}. "
            f"This violates the intended architecture: Watcher → Engine → Fusion → Strategy → Broker. "
            f"The Watcher should only emit market observations, not execute trades."
        )

        # Raise an exception to prevent this architectural violation
        raise RuntimeError(
            f"Watcher layer attempted to execute trade directly for {execution_intent.symbol.value}. "
            f"This is an architectural violation. The Watcher should only emit market observations."
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the watcher."""
        return {
            'is_running': self.is_running,
            'monitored_symbols': [s.value for s in self.symbols],
            'watchers_count': sum(len(watchers) for watchers in self.watchers.values()),
            'last_observations': {k: list(v.keys()) for k, v in self.last_observations.items()},  # Updated to observations
            'timestamp': datetime.now().isoformat()
        }
