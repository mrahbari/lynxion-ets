"""
Market Opportunity Watcher for auto-detection system.
Monitors markets continuously and identifies opportunities based on technical conditions.
"""
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol
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
from shared.logger import EnhancedLogger


class MarketOpportunityWatcher:
    """Watches markets continuously to detect trading opportunities and trigger strategies."""

    def __init__(self, symbols: Optional[List[str]] = None,
                 opportunity_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                 auto_discover_symbols: bool = False):
        self.auto_discover_symbols = auto_discover_symbols
        self.opportunity_callback = opportunity_callback
        self.logger = EnhancedLogger("MarketOpportunityWatcher")
        self.is_running = False
        self.watchers = {}
        self.last_signals = {}
        self.monitoring_thread = None

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

                all_discovered_symbols.update(symbols)

            # Also add symbols from general market discovery to ensure comprehensive coverage
            general_symbols = self._discover_by_market_cap()
            all_discovered_symbols.update(general_symbols)

            discovered_symbols = list(all_discovered_symbols)

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
            fallback_symbols_str = os.getenv("FALLBACK_WATCHLIST_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,AVAXUSDT,MATICUSDT,DOTUSDT,LINKUSDT")
            fallback_symbols = [s.strip() for s in fallback_symbols_str.split(",")]
            discovered_symbols = fallback_symbols

        # Filter out stablecoin-to-stablecoin pairs (e.g., USDTUSDT, USDCUSDT, etc.)
        filtered_symbols = self._filter_stablecoin_pairs(discovered_symbols)

        self.logger.info(f"✅ Auto-discovered {len(filtered_symbols)} symbols to monitor: {filtered_symbols}")
        return [Symbol(s) for s in filtered_symbols]

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
                    if change_abs > 3.0 and ticker['quoteVolume'] and ticker['quoteVolume'] > 1000000:  # 3%+ change and high volume
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
                    volatility = abs((ticker['high'] - ticker['low']) / ticker['open']) * 100 if ticker['open'] != 0 else 0

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
                    market.get('active', True)):    # Check if active

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
        stablecoin_bases_str = os.getenv("STABLECOIN_BASES", "USDT,USDC,BUSD,DAI,TUSD,PAX,USDD,FDUSD,TERRA,FRAX,LUSD,FEI,ALUSD,GUSD,HUSD,EURT,USDK,RSV,PYUSD,EURS,USDP,TUSDS")
        stablecoin_bases = set(coin.strip().upper() for coin in stablecoin_bases_str.split(',') if coin.strip())

        filtered_symbols = []
        for symbol in symbols:
            # Extract base and quote currencies (assuming format like BTCUSDT, ETHUSDC, etc.)
            # For symbols like BTCUSDT, we need to find where the base currency ends and quote currency begins
            base_currency = None
            quote_currency = None

            # Check for common quote currencies at the end of the symbol
            for quote in sorted(stablecoin_bases, key=len, reverse=True):  # Sort by length descending to match longer quotes first
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
                    self.logger.debug(f"⏭️  Filtering out stablecoin pair: {symbol} ({base_currency} -> {quote_currency})")
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
            cmc_listings_url = os.getenv("CMC_LISTINGS_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

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
                    excluded_coins_str = os.getenv("CMC_EXCLUDED_COINS", "BTC,ETH,SOL,ADA,DOT,XRP,DOGE,LINK,BNB,AVAX,MATIC,BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT,DOTUSDT,XRPUSDT,DOGEUSDT,LINKUSDT,BNBUSDT,AVAXUSDT,MATICUSDT")
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
                if not all(key in ticker for key in ['close', 'high', 'low', 'quoteVolume', 'change', 'changePercentage']):
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
            important_symbols = [coin for coin in major_coins if coin not in [item['symbol'] for item in active_symbols]]

            # Combine and limit to 10
            final_symbols = (top_active + important_symbols)[:10]

            self.logger.info(f"📈 Found {len(final_symbols)} active symbols based on recent activity")
            return final_symbols

        except Exception as e:
            self.logger.warning(f"Error during recent activity symbol discovery: {e}")
            # Fallback to basic discovery if activity detection fails
            return self._discover_symbols_automatically()
        
    def _initialize_watchers(self):
        """Initialize watcher adapters for each symbol - only if enabled."""
        for symbol in self.symbols:
            symbol_watchers = {}

            # Check each watcher type before creating to avoid unnecessary instantiation
            if os.getenv('MARKET_PULSE_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['market_pulse'] = MarketPulseWatcher("MarketPulse", symbol.value)

            if os.getenv('VOLATILITY_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['volatility'] = VolatilityWatcher("Volatility", symbol.value)

            if os.getenv('TREND_MTF_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['trend_mtf'] = TrendMTFWatcher("TrendMTF", symbol.value)

            if os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['anomaly_ml'] = AnomalyMLWatcher("AnomalyML", symbol.value)

            if os.getenv('ORDERFLOW_WS_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['orderflow_ws'] = OrderFlowWSWatcher("OrderFlowWS", symbol.value)

            if os.getenv('CMC_SCREENER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['cmc_screener'] = CMCScreener(name=f"CMCWatcher_{symbol.value}", symbol=symbol.value)

            if os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['funding_rate'] = FundingRateWatcher("FundingRate", symbol.value)

            if os.getenv('LIQUIDITY_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['liquidity'] = LiquidityWatcher("Liquidity", symbol.value)

            if os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true':
                symbol_watchers['historical_candle'] = HistoricalCandleWatcherAdapter("HistoricalCandle", symbol.value, None)

            if os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true':
                # For TickWatcher, we need a broker service - using a placeholder for now
                # In a real implementation, this would be properly configured
                from infrastructure.brokers.broker_manager import BrokerManager
                broker_service = BrokerManager()  # This would be the proper broker service
                symbol_watchers['tick_watcher'] = TickWatcherAdapter("TickWatcher", symbol.value, broker_service)

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
        
        while self.is_running:
            try:
                self._check_market_opportunities()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Continue monitoring even if there's an error
                
    def _check_market_opportunities(self):
        """Check each symbol for trading opportunities."""
        for symbol in self.symbols:
            opportunities = self._analyze_symbol(symbol)
            if opportunities:
                self._process_opportunities(symbol, opportunities)
                
    def _analyze_symbol(self, symbol: Symbol) -> Dict[str, Any]:
        """Analyze a symbol using all available watchers - only if enabled."""
        symbol_str = symbol.value
        opportunities = {
            'symbol': symbol_str,
            'timestamp': datetime.now(),
            'signals': {},
            'indicators': {},
            'recommendation': None,
            'confidence': 0.0,
            'strategy_suggestion': None
        }

        # Analyze with each watcher - only if the watcher is enabled
        for watcher_name, watcher in self.watchers[symbol_str].items():
            # Check if the specific watcher has an enabled attribute and if it's enabled
            watcher_is_enabled = True  # Default assumption

            # Check if the watcher has an enabled attribute
            if hasattr(watcher, 'enabled'):
                watcher_is_enabled = watcher.enabled

            # Only call analyze if the watcher is enabled
            if watcher_is_enabled:
                try:
                    signal = watcher.analyze(symbol)
                    if signal:
                        opportunities['signals'][watcher_name] = {
                            'signal_type': signal.signal_type.name,
                            'confidence': float(signal.confidence.value) if hasattr(signal.confidence, 'value') else float(signal.confidence),
                            'score': signal.score,
                            'timestamp': signal.timestamp.isoformat() if hasattr(signal, 'timestamp') else datetime.now().isoformat(),
                            'metadata': signal.metadata if hasattr(signal, 'metadata') else {}
                        }

                        # Determine overall recommendation based on signals
                        if signal.signal_type.name in ['BUY', 'SELL']:
                            opportunities['recommendation'] = signal.signal_type.name
                            opportunities['confidence'] = max(opportunities['confidence'], float(signal.confidence.value) if hasattr(signal.confidence, 'value') else float(signal.confidence))

                            # Suggest strategy based on signal type and characteristics
                            opportunities['strategy_suggestion'] = self._suggest_strategy_for_signal(signal)
                except Exception as e:
                    self.logger.error(f"Error analyzing {symbol_str} with {watcher_name}: {e}")
                    continue

        return opportunities
        
    def _suggest_strategy_for_signal(self, signal: Signal) -> str:
        """Suggest the most appropriate strategy based on signal characteristics."""
        # Determine strategy based on signal source and characteristics
        if 'momentum' in signal.metadata.get('indicator', '').lower():
            return 'momentum_strategy'
        elif signal.metadata.get('volatility') and signal.metadata['volatility'] > 0.5:
            return 'volatility_strategy'
        elif 'trend' in signal.source_engine.lower():
            return 'trend_following'
        elif 'anomaly' in signal.source_engine.lower():
            return 'mean_reversion'
        elif 'order_flow' in signal.source_engine.lower():
            return 'order_flow'
        else:
            return 'balanced_strategy'
            
    def _process_opportunities(self, symbol: Symbol, opportunities: Dict[str, Any]):
        """Process detected opportunities and trigger callback if available."""
        if opportunities['recommendation'] and opportunities['confidence'] > 0.6:  # Only if confidence is high enough
            self.logger.log_opportunity_detected(
                symbol.value,
                opportunities['recommendation'],
                opportunities['confidence'],
                opportunities['strategy_suggestion']
            )

            if self.opportunity_callback:
                try:
                    self.opportunity_callback(opportunities)
                except Exception as e:
                    self.logger.error(f"Error in opportunity callback: {e}")
                    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the watcher."""
        return {
            'is_running': self.is_running,
            'monitored_symbols': [s.value for s in self.symbols],
            'watchers_count': sum(len(watchers) for watchers in self.watchers.values()),
            'last_signals': {k: list(v.keys()) for k, v in self.last_signals.items()},
            'timestamp': datetime.now().isoformat()
        }