"""
Market Opportunity Watcher for auto-detection system.
Monitors markets continuously and identifies opportunities based on technical conditions.
Following correct architecture: Watchers only produce raw market observations.
"""
import os
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


# Import all watcher adapters that are used in the initialization
from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
from infrastructure.watchers.adapters.volatility import VolatilityWatcher
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
from infrastructure.watchers.adapters.cmc_screener import CMCScreener
from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
from infrastructure.watchers.adapters.liquidity import LiquidityWatcher
from infrastructure.watchers.adapters.historical_candle_watcher import HistoricalCandleWatcherAdapter
from infrastructure.watchers.adapters.tick_watcher import TickWatcherAdapter


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

        # If no symbols provided and auto-discovery is enabled, discover symbols dynamically
        if auto_discover_symbols and not symbols:
            self.symbols = self._discover_symbols_automatically()
        elif symbols:
            # Convert symbol format if needed (e.g., BTC/USDT -> BTCUSDT)
            converted_symbols = []
            for s in symbols:
                # Convert from BTC/USDT format to BTCUSDT format if slash is present
                if '/' in s:
                    s = s.replace('/', '')
                converted_symbols.append(Symbol(s))
            self.symbols = converted_symbols
        else:
            # Use default symbols from environment variables or fallback to hard-coded defaults
            default_symbols = os.getenv("DEFAULT_WATCHLIST_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT").split(",")
            self.symbols = [Symbol(s.strip()) for s in default_symbols]

        # Initialize watcher adapters for each symbol
        self._initialize_watchers()

    def _discover_symbols_automatically(self) -> List[Symbol]:
        """Dynamically discover symbols to monitor based on market conditions or other criteria."""
        self.logger.info("🔍 Discovering symbols to monitor automatically...")

        # Check which watcher types are enabled to determine appropriate discovery method
        market_pulse_enabled = os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true'
        volatility_enabled = os.getenv('VOLATILITY_WATCHER_ENABLED', 'false').lower() == 'true'
        trend_mtf_enabled = os.getenv('TREND_MTF_WATCHER_ENABLED', 'false').lower() == 'true'
        anomaly_ml_enabled = os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'false').lower() == 'true'
        orderflow_ws_enabled = os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'false').lower() == 'true'
        cmc_screener_enabled = os.getenv('CMC_SCREENER_ENABLED', 'false').lower() == 'true'
        funding_rate_enabled = os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'false').lower() == 'true'
        liquidity_enabled = os.getenv('LIQUIDITY_WATCHER_ENABLED', 'false').lower() == 'true'
        historical_candle_enabled = os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'false').lower() == 'true'
        tick_watcher_enabled = os.getenv('TICK_WATCHER_ENABLED', 'false').lower() == 'true'

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

        # When multiple watchers are enabled, we should potentially use a combined discovery approach
        # that captures symbols relevant to all enabled watcher types
        if len(enabled_watchers) == 0:
            # If no watchers are enabled, use default discovery
            discovered_symbols = self._discover_by_market_cap()
        elif len(enabled_watchers) == 1:
            # If only one watcher is enabled, use its specific discovery method
            watcher_type = enabled_watchers[0]
            if watcher_type == 'trend_mtf':
                discovered_symbols = self._discover_trend_oriented_symbols()
            elif watcher_type == 'volatility':
                discovered_symbols = self._discover_volatility_oriented_symbols()
            elif watcher_type == 'market_pulse':
                discovered_symbols = self._discover_momentum_oriented_symbols()
            elif watcher_type == 'anomaly_ml':
                discovered_symbols = self._discover_anomaly_oriented_symbols()
            elif watcher_type == 'orderflow_ws':
                discovered_symbols = self._discover_orderflow_oriented_symbols()
            elif watcher_type == 'funding_rate':
                discovered_symbols = self._discover_funding_oriented_symbols()
            elif watcher_type == 'liquidity':
                discovered_symbols = self._discover_liquidity_oriented_symbols()
            elif watcher_type == 'historical_candle':
                discovered_symbols = self._discover_historical_candle_oriented_symbols()
            elif watcher_type == 'cmc_screener':
                discovered_symbols = self._discover_by_market_cap()
            elif watcher_type == 'tick_watcher':
                discovered_symbols = self._discover_tick_oriented_symbols()
            else:
                discovered_symbols = self._discover_by_market_cap()
        else:
            # When multiple watchers are enabled, we want to ensure comprehensive coverage
            # Rather than choosing one discovery method, we should combine results from multiple discovery methods
            # to ensure symbols relevant to all watcher types are included
            watcher_specific_symbols = {}
            all_discovered_symbols = set()

            # Add symbols from each enabled watcher type's specific discovery method
            for watcher_type in enabled_watchers:
                if watcher_type == 'trend_mtf':
                    symbols = self._discover_trend_oriented_symbols()
                elif watcher_type == 'volatility':
                    symbols = self._discover_volatility_oriented_symbols()
                elif watcher_type == 'market_pulse':
                    symbols = self._discover_momentum_oriented_symbols()
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
                if hasattr(self, 'logger') and symbols:
                    self.logger.info(
                        f"🔍 {watcher_type.upper()} WATCHER DISCOVERED: {len(symbols)} symbols - {symbols[:5]}{'...' if len(symbols) > 5 else ''}",
                        watcher_type=watcher_type,
                        symbols_discovered=len(symbols),
                        sample_symbols=symbols[:5])

            # Also add symbols from general market discovery to ensure comprehensive coverage
            general_symbols = self._discover_by_market_cap()
            all_discovered_symbols.update(general_symbols)

            discovered_symbols = list(all_discovered_symbols)

            # Store the watcher-specific symbols for later use in _initialize_watchers
            self._watcher_specific_symbols = watcher_specific_symbols

            # Log the combined symbol set
            if hasattr(self, 'logger'):
                self.logger.info(
                    f"📊 COMBINED SYMBOLS: {len(discovered_symbols)} total symbols after combining {len(enabled_watchers)} watcher types",
                    total_symbols=len(discovered_symbols),
                    watcher_count=len(enabled_watchers),
                    watcher_specific=watcher_specific_symbols)

        # Ensure we have a good mix of symbols that would be relevant for all enabled watchers
        # If the discovered symbols are too limited, expand to include more general market symbols
        if len(discovered_symbols) < 10 and len(enabled_watchers) > 0:
            # If we have enabled watchers but not enough symbols discovered, expand the discovery
            additional_symbols = self._discover_by_market_cap()
            all_symbols = list(set(discovered_symbols + additional_symbols))
            discovered_symbols = all_symbols[:15]  # Limit to 15 symbols max

        # If no specific discovery method worked, fall back to price activity
        if not discovered_symbols:
            discovered_symbols = self._discover_by_price_activity()

        # If still no symbols found, use fallback symbols
        if not discovered_symbols:
            fallback_symbols_str = os.getenv("FALLBACK_WATCHLIST_SYMBOLS",
                                             "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,AVAXUSDT,TRXUSDT,DOTUSDT,LINKUSDT")
            fallback_symbols = [s.strip() for s in fallback_symbols_str.split(",")]
            discovered_symbols = fallback_symbols

        # Filter out stablecoin-to-stablecoin pairs (e.g., USDTUSDT, USDCUSDT, etc.)
        filtered_symbols = self._filter_stablecoin_pairs(discovered_symbols)

        # Filter symbols and handle invalid ones gracefully
        valid_symbols = []
        for symbol in filtered_symbols:
            try:
                # Try to create a Symbol object to validate it
                Symbol(symbol)  # This will raise ValueError if invalid
                valid_symbols.append(symbol)
            except ValueError:
                # Log the invalid symbol but continue processing others
                self.logger.warning(f"Skipping invalid symbol: {symbol}")
                continue

        self.logger.info(f"✅ Auto-discovered {len(valid_symbols)} symbols to monitor: {valid_symbols}")
        # Convert to Symbol objects only for valid ones
        return [Symbol(symbol) for symbol in valid_symbols]

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
                        trending_symbols.append(formatted_symbol)
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
                            volatile_symbols.append(formatted_symbol)
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
                        momentum_symbols.append(formatted_symbol)
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
                        anomaly_symbols.append(formatted_symbol)
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
                        high_volume_symbols.append(formatted_symbol)
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
                            liquid_symbols.append(formatted_symbol)
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
                    perp_symbols.append(formatted_symbol)

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

    def _filter_stablecoin_pairs(self, symbols: List[str]) -> List[str]:
        """Filter out stablecoin-to-stablecoin pairs like USDTUSDT, USDCUSDT, etc."""
        # Get stablecoin bases from environment variable
        stablecoin_bases_str = os.getenv("STABLECOIN_BASES",
                                         "USDT,USDC,BUSD,DAI,TUSD,PAX,USDD,FDUSD,TERRA,FRAX,LUSD,FEI,ALUSD,GUSD,HUSD,EURT,USDK,RSV,PYUSD,EURS,USDP,TUSDS")
        stablecoin_bases = set(coin.strip().upper() for coin in stablecoin_bases_str.split(',') if coin.strip())

        filtered_symbols = []
        for symbol in symbols:
            # Extract base and quote currencies (assuming format like BTCUSDT, ETHUSDC, etc.)
            # For symbols like BTCUSDT, we need to find where the base currency ends and quote currency begins
            base_currency = None
            quote_currency = None

            # Check for common quote currencies at the end of the symbol
            for quote in sorted(stablecoin_bases, key=len,
                                reverse=True):  # Sort by length descending to match longer quotes first
                if symbol.endswith(quote):
                    base_part = symbol[:-len(quote)]
                    if base_part:  # Make sure there's a base currency part
                        base_currency = base_part
                        quote_currency = quote
                        break

            # If we have both base and quote currencies
            if base_currency and quote_currency:
                # Skip if both are stablecoins (stablecoin to stablecoin pair)
                if base_currency in stablecoin_bases and quote_currency in stablecoin_bases:
                    # Note: The logger here will be a mock logger if this watcher is disabled,
                    # so this debug message won't appear when disabled
                    self.logger.debug(
                        f"⏭️  Filtering out stablecoin pair: {symbol} ({base_currency} -> {quote_currency})")
                    continue
                # Skip if it's the same currency pair like USDTUSDT
                elif base_currency == quote_currency:
                    # Note: The logger here will be a mock logger if this watcher is disabled,
                    # so this debug message won't appear when disabled
                    self.logger.debug(f"⏭️  Filtering out same-currency pair: {symbol}")
                    continue
                else:
                    # Valid pair, add to filtered symbols
                    filtered_symbols.append(symbol)
            else:
                # If we can't parse the symbol properly, still add it (conservative approach)
                # This handles cases where the symbol doesn't match our expected patterns
                filtered_symbols.append(symbol)

        return filtered_symbols

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
                            Symbol(formatted_symbol)  # This will validate the format
                            discovered_symbols.append(formatted_symbol)
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
                    top_symbols.append(formatted)
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
                        historical_oriented_symbols.append(formatted_symbol)

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
                        tick_oriented_symbols.append(formatted_symbol)

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
                        high_volume_symbols.append(formatted_symbol)

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

        # Use activity-based discovery for more timely updates
        current_symbols = [s.value for s in self.symbols]
        new_symbols = self._discover_by_recent_activity()
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

                if Symbol(symbol_str) in self.symbols:
                    self.symbols.remove(Symbol(symbol_str))

            # Add watchers for new symbols
            for symbol_str in added_symbols:
                symbol = Symbol(symbol_str)
                if symbol not in self.symbols:  # Avoid duplicates
                    self.symbols.append(symbol)
                    self.watchers[symbol_str] = {
                        'market_pulse': MarketPulseWatcherAdapter(symbol),
                        'volatility': VolatilityWatcherAdapter(symbol),
                        'trend_mtf': TrendMTFWatcherAdapter(symbol),
                        'anomaly_ml': AnomalyMLWatcherAdapter(symbol),
                        'order_flow': OrderFlowWatcherAdapter(symbol),
                        'cmc_watcher': CMCScreener(name=f"CMCWatcher_{symbol.value}", symbol=symbol.value),
                    }
                    # Start new watchers
                    for watcher_name, watcher in self.watchers[symbol_str].items():
                        if hasattr(watcher, 'start'):
                            watcher.start()

            # Update symbol list to match the new discovery
            self.symbols = new_symbols
        else:
            self.logger.debug(f"✅ Symbol list unchanged: {len(current_symbols)} symbols")

    def _discover_by_recent_activity(self) -> List[Symbol]:
        """Discover symbols based on recent market activity like volume surges or price movements."""
        try:
            # This method focuses on recent market activity rather than just market cap
            import ccxt
            import time

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
            return self._discover_symbols_automatically()

    def _initialize_watchers(self):
        """Initialize watcher adapters for each symbol based on which watcher discovered it - only if enabled."""

        # First, let's track which symbols were discovered by which watcher type
        # This information is available in self._discover_symbols_automatically()
        # We need to track the original discovery mapping

        # Create a mapping of symbols to their primary watcher based on discovery
        symbol_to_primary_watcher = {}

        # If we're in auto-discovery mode, we know which watcher discovered which symbols
        if hasattr(self, '_watcher_specific_symbols'):
            for watcher_type, symbols in self._watcher_specific_symbols.items():
                # Check if this watcher type is enabled
                env_var = f"{watcher_type.upper()}_WATCHER_ENABLED"
                if os.getenv(env_var, 'true').lower() == 'true':
                    for symbol in symbols:
                        # Assign this watcher as the primary watcher for this symbol
                        if symbol not in symbol_to_primary_watcher:
                            symbol_to_primary_watcher[symbol] = set()
                        symbol_to_primary_watcher[symbol].add(watcher_type)

        for symbol in self.symbols:
            symbol_watchers = {}

            # Check each watcher type before creating to avoid unnecessary instantiation
            # Only create watchers that are relevant to this symbol or if it's a general watcher

            # Market Pulse watcher
            if os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true':
                # Check if this symbol was discovered by market pulse watcher
                if (symbol.value in symbol_to_primary_watcher and
                        'market_pulse' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['market_pulse'] = MarketPulseWatcher("MarketPulse", symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"MarketPulse assigned to {symbol.value} (discovered by MarketPulse)",
                            symbol=symbol.value,
                            watcher="market_pulse",
                            discovery_source="market_pulse"
                        )
                elif not symbol_to_primary_watcher:  # If no specific mapping (fallback to original behavior)
                    symbol_watchers['market_pulse'] = MarketPulseWatcher("MarketPulse", symbol.value)

            # Volatility watcher
            if os.getenv('VOLATILITY_WATCHER_ENABLED', 'true').lower() == 'true':
                # Check if this symbol was discovered by volatility watcher
                if (symbol.value in symbol_to_primary_watcher and
                        'volatility' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['volatility'] = VolatilityWatcher("Volatility", symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"Volatility assigned to {symbol.value} (discovered by Volatility)",
                            symbol=symbol.value,
                            watcher="volatility",
                            discovery_source="volatility"
                        )
                elif not symbol_to_primary_watcher:  # If no specific mapping (fallback to original behavior)
                    symbol_watchers['volatility'] = VolatilityWatcher("Volatility", symbol.value)

            # Trend MTF watcher
            if os.getenv('TREND_MTF_WATCHER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'trend_mtf' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['trend_mtf'] = TrendMTFWatcher("TrendMTF", symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"TrendMTF assigned to {symbol.value} (discovered by TrendMTF)",
                            symbol=symbol.value,
                            watcher="trend_mtf",
                            discovery_source="trend_mtf"
                        )
                elif not symbol_to_primary_watcher:
                    symbol_watchers['trend_mtf'] = TrendMTFWatcher("TrendMTF", symbol.value)

            # Anomaly ML watcher
            if os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'anomaly_ml' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['anomaly_ml'] = AnomalyMLWatcher("AnomalyML", symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"AnomalyML assigned to {symbol.value} (discovered by AnomalyML)",
                            symbol=symbol.value,
                            watcher="anomaly_ml",
                            discovery_source="anomaly_ml"
                        )
                elif not symbol_to_primary_watcher:
                    symbol_watchers['anomaly_ml'] = AnomalyMLWatcher("AnomalyML", symbol.value)

            # OrderFlow WS watcher
            if os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'orderflow_ws' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['orderflow_ws'] = OrderFlowWSWatcher("OrderFlowWS", symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"OrderFlowWS assigned to {symbol.value} (discovered by OrderFlowWS)",
                            symbol=symbol.value,
                            watcher="orderflow_ws",
                            discovery_source="orderflow_ws"
                        )
                elif not symbol_to_primary_watcher:
                    symbol_watchers['orderflow_ws'] = OrderFlowWSWatcher("OrderFlowWS", symbol.value)

            # CMC Screener watcher
            if os.getenv('CMC_SCREENER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'cmc_screener' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['cmc_screener'] = CMCScreener(name=f"CMCWatcher_{symbol.value}",
                                                                  symbol=symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"CMCScreener assigned to {symbol.value} (discovered by CMCScreener)",
                            symbol=symbol.value,
                            watcher="cmc_screener",
                            discovery_source="cmc_screener"
                        )
                elif not symbol_to_primary_watcher:
                    symbol_watchers['cmc_screener'] = CMCScreener(name=f"CMCWatcher_{symbol.value}",
                                                                  symbol=symbol.value)

            # Funding Rate watcher
            if os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'funding_rate' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['funding_rate'] = FundingRateWatcher("FundingRate", symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"FundingRate assigned to {symbol.value} (discovered by FundingRate)",
                            symbol=symbol.value,
                            watcher="funding_rate",
                            discovery_source="funding_rate"
                        )
                elif not symbol_to_primary_watcher:
                    symbol_watchers['funding_rate'] = FundingRateWatcher("FundingRate", symbol.value)

            # Liquidity watcher
            if os.getenv('LIQUIDITY_WATCHER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'liquidity' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['liquidity'] = LiquidityWatcher("Liquidity", symbol.value)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"Liquidity assigned to {symbol.value} (discovered by Liquidity)",
                            symbol=symbol.value,
                            watcher="liquidity",
                            discovery_source="liquidity"
                        )
                elif not symbol_to_primary_watcher:
                    symbol_watchers['liquidity'] = LiquidityWatcher("Liquidity", symbol.value)

            # Historical Candle watcher
            if os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'historical_candle' in symbol_to_primary_watcher[symbol.value]):
                    symbol_watchers['historical_candle'] = HistoricalCandleWatcherAdapter("HistoricalCandle",
                                                                                          symbol.value, None)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"HistoricalCandle assigned to {symbol.value} (discovered by HistoricalCandle)",
                            symbol=symbol.value,
                            watcher="historical_candle",
                            discovery_source="historical_candle"
                        )
                elif not symbol_to_primary_watcher:
                    symbol_watchers['historical_candle'] = HistoricalCandleWatcherAdapter("HistoricalCandle",
                                                                                          symbol.value, None)

            # Tick Watcher
            if os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true':
                if (symbol.value in symbol_to_primary_watcher and
                        'tick_watcher' in symbol_to_primary_watcher[symbol.value]):
                    from infrastructure.brokers.broker_manager import BrokerManager
                    broker_service = BrokerManager()
                    symbol_watchers['tick_watcher'] = TickWatcherAdapter("TickWatcher", symbol.value, broker_service)
                    if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                        self.logger.log_background_activity(
                            "Watcher Assignment",
                            f"TickWatcher assigned to {symbol.value} (discovered by TickWatcher)",
                            symbol=symbol.value,
                            watcher="tick_watcher",
                            discovery_source="tick_watcher"
                        )
                elif not symbol_to_primary_watcher:
                    # Use the market data repo instead of execution service since we removed direct service access
                    symbol_watchers['tick_watcher'] = TickWatcherAdapter("TickWatcher", symbol.value, self.market_data_repo)

            self.watchers[symbol.value] = symbol_watchers

            # Start only the enabled watchers - double check enabled status
            for watcher_name, watcher in self.watchers[symbol.value].items():
                # Double-check the watcher's enabled status before starting
                if getattr(watcher, 'enabled', True):
                    watcher.start()

    def start_monitoring(self):
        """Start continuous market monitoring."""
        if self.is_running:
            self.logger.warning("Market opportunity watcher is already running")
            return

        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.log_auto_detection_status(len(self.symbols), 0, 0)

    def stop_monitoring(self):
        """Stop market monitoring."""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish

        # Stop all watchers
        for symbol_watchers in self.watchers.values():
            for watcher in symbol_watchers.values():
                watcher.stop()

        self.logger.info("🛑 Market opportunity monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop that continuously checks for opportunities."""
        self.logger.info("🔄 Market opportunity monitoring loop started")

        # Track statistics for periodic reporting
        last_report_time = time.time()
        report_interval = 60  # seconds between detailed reports
        analysis_count = 0
        signals_found = 0

        while self.is_running:
            try:
                opportunities = self._check_market_opportunities()
                analysis_count += len(self.symbols)

                # Count signals found
                for opportunity in opportunities:
                    if opportunity.get('recommendation') and opportunity['confidence'] > 0.6:
                        signals_found += 1

                # Log periodic detailed reports
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    self.logger.info(
                        f"📊 WATCHER ANALYTICS: Analyzed {analysis_count} symbol checks in last {report_interval}s | "
                        f"Signals found: {signals_found} | Monitored symbols: {len(self.symbols)}")
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

        # Then analyze each symbol
        for symbol in self.symbols:
            opportunities = self._analyze_symbol(symbol)
            if opportunities:
                self._process_opportunities(symbol, opportunities)
                all_opportunities.append(opportunities)
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
                    historical_data = self.market_data_repo.get_historical_data(Symbol(symbol.value), "30m", "1m")
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
            'execution_intent': None
        }

        # Process each watcher individually - only emit raw market observations
        for watcher_name, watcher in self.watchers[symbol_str].items():
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

    def _process_opportunities(self, symbol: Symbol, opportunities: Dict[str, Any]):
        """Process detected opportunities and trigger callback if available."""
        if opportunities['recommendation'] and opportunities['confidence'] > 0.6:  # Only if confidence is high enough
            self.logger.log_opportunity_detected(
                symbol.value,
                opportunities['recommendation'],
                opportunities['confidence'],
                opportunities['strategy_suggestion']
            )

            # Log the flow from watcher to the next component (engine)
            self.logger.log_watcher_to_engine_flow(
                symbol=symbol.value,
                watcher_name="MarketOpportunityWatcher",
                signal_generated=bool(opportunities['recommendation']),
                signal_type=opportunities['recommendation'],
                confidence=opportunities['confidence'],
                reason=f"Opportunity detected with confidence {opportunities['confidence']:.2%}",
            )

            # Log background activity in comprehensive mode
            if hasattr(self.logger, 'comprehensive_mode') and self.logger.comprehensive_mode:
                self.logger.log_background_activity(
                    "Opportunity Processing",
                    f"Processing opportunity for {symbol.value} - {opportunities['recommendation']} with confidence {opportunities['confidence']:.2%}",
                    symbol=symbol.value,
                    recommendation=opportunities['recommendation'],
                    confidence=opportunities['confidence']
                )

            if self.opportunity_callback:
                try:
                    self.opportunity_callback(opportunities)
                except Exception as e:
                    self.logger.error(f"Error in opportunity callback: {e}")

    def _execute_intent_trade(self, execution_intent):
        """Execute a trade based on the execution intent from the Strategy layer."""
        if not self.execution_service:
            self.logger.warning(f"No execution service available to execute intent for {execution_intent.symbol.value}")
            return None

        try:
            # Get current price for the symbol to determine position size
            current_price = None
            if self.market_data_repo:
                try:
                    current_price = self.market_data_repo.get_current_price(execution_intent.symbol)
                except:
                    # If we can't get current price from data repo, try to get from exchange directly
                    pass

            # If we still don't have a price, use a fallback
            if current_price is None or current_price <= 0:
                # Try to get price from exchange directly
                try:
                    import ccxt
                    exchange = ccxt.binance()
                    ticker = exchange.fetch_ticker(execution_intent.symbol.value)
                    current_price = ticker['last'] if 'last' in ticker else ticker['close']
                except:
                    # If all methods fail, we'll still proceed but log the issue
                    self.logger.warning(f"Could not get current price for {execution_intent.symbol.value}, using default price")
                    current_price = 50000.0  # Fallback price

            # Use risk parameters from the execution intent
            risk_params = execution_intent.risk_parameters
            position_size_pct = risk_params.get('max_position_size', 0.02)  # Default 2%

            # Fixed Position Size Configuration (for testing purposes)
            import os
            fixed_position_size_enabled = os.getenv('FIXED_POSITION_SIZE_ENABLED', 'false').lower() == 'true'
            fixed_position_amount = float(os.getenv('FIXED_POSITION_AMOUNT', '10.0'))  # Default to $10 for testing

            # Calculate quantity based on risk parameters and account balance
            try:
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    quantity = fixed_position_amount / current_price
                    self.logger.info(f"Using fixed position size: ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # In a real implementation, we'd get portfolio metrics from portfolio service
                    # For now, using a default account balance from environment variable
                    import os
                    account_balance = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '10000.0'))  # Default to $10,000 if not available
                    position_value = account_balance * position_size_pct

                    # Calculate quantity based on position value and current price
                    quantity = position_value / current_price

                    # Apply any quantity adjustments from risk parameters
                    if 'position_quantity' in risk_params:
                        quantity = risk_params['position_quantity']

            except:
                # If portfolio service fails, use a default quantity
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    quantity = fixed_position_amount / current_price
                    self.logger.info(f"Using fixed position size (fallback): ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # Use default account balance from environment variable
                    import os
                    default_account_balance = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '1000.0'))  # Default to $1,000 if not available
                    quantity = position_size_pct * default_account_balance / current_price

            # Ensure minimum quantity to avoid issues with small trades
            if quantity < 0.001:
                quantity = 0.001  # Minimum trade size

            # Create order object using domain entities
            from domain.entities.signal_entities import Order, OrderSide
            from domain.value_objects import Money

            # Use the side from the execution intent
            order_side = execution_intent.side

            # Determine position side based on order side for futures trading
            position_side = "LONG" if order_side.name == 'BUY' else "SHORT"

            # Ensure symbol is properly formatted for the broker
            symbol_value = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)

            # Create order with proper risk parameters from the intent
            order = Order(
                symbol=symbol_value,  # Use string value instead of Symbol object
                side=order_side,
                order_type="MARKET",  # Using string instead of enum
                quantity=quantity,
                price=Money(amount=current_price, currency='USDT') if current_price else None,
                strategy_name=execution_intent.strategy_name,  # Strategy name comes from intent
                timestamp=datetime.now(),
                position_side=position_side,  # Add position side for futures trading
                stop_loss_price=Money(amount=risk_params.get('stop_loss_price', current_price * 0.98), currency='USDT'),  # Default SL
                take_profit_price=Money(amount=risk_params.get('take_profit_price', current_price * 1.03), currency='USDT'),  # Default TP
                parent_execution_intent=execution_intent  # Link back to the execution intent
            )

            # Validate symbol availability before executing order
            if hasattr(self.execution_service, 'get_available_symbols'):
                available_symbols = self.execution_service.get_available_symbols()
                if symbol_value not in available_symbols:
                    self.logger.warning(f"⚠️ Symbol {symbol_value} not available on any configured broker. Skipping order.")
                    return None  # Skip execution if symbol is not available

            # Execute order through execution service
            execution_id = self.execution_service.execute_order(order)

            # Log the successful execution with detailed information
            # Handle both string and object formats for symbol and side
            symbol_log_value = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
            side_log_value = order.side.name if hasattr(order.side, 'name') else str(order.side)

            confidence = float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5

            self.logger.info(
                f"⚡ TRADE EXECUTED: {side_log_value} {quantity:.4f} {symbol_log_value} @ ${current_price:.4f} | Strategy: {execution_intent.strategy_name} | Intent Conf: {confidence:.2%}",
                order_id=execution_id,
                symbol=symbol_log_value,
                side=side_log_value,
                quantity=quantity,
                price=current_price,
                strategy=execution_intent.strategy_name,
                confidence=confidence
            )

            # Log the execution in the signal progression
            self.logger.log_signal_progression(
                symbol=symbol_log_value,
                stage="broker",
                status="Executed",
                details=f"Order executed successfully from strategy intent: {execution_id}",
                confidence=confidence
            )

            return execution_id
        except Exception as e:
            import traceback
            self.logger.error(f"Error executing trade from strategy intent: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Log the execution failure
            self.logger.log_signal_progression(
                symbol=execution_intent.symbol.value,
                stage="broker",
                status="Failed",
                details=f"Order execution from strategy intent failed: {str(e)}",
                confidence=float(execution_intent.intent_confidence.value) if hasattr(execution_intent.intent_confidence, 'value') else 0.5
            )
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the watcher."""
        return {
            'is_running': self.is_running,
            'monitored_symbols': [s.value for s in self.symbols],
            'watchers_count': sum(len(watchers) for watchers in self.watchers.values()),
            'last_observations': {k: list(v.keys()) for k, v in self.last_observations.items()},  # Updated to observations
            'timestamp': datetime.now().isoformat()
        }
