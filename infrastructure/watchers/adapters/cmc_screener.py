"""
CMC Screener - Optimized CoinMarketCap Screener following watcher perfection requirements
"""
import os
import requests
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from decimal import Decimal
from threading import Lock

from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.watcher_ports import WatcherPort
from shared.logger import EnhancedLogger
from dotenv import load_dotenv


class CMCScreener(WatcherPort):
    """Optimized CoinMarketCap Screener - provides universe signals, not trade signals."""

    def __init__(self, name: str = "CMCScreener", symbol: str = "BTCUSDT"):
        self.name = name
        self.symbol = Symbol(symbol)
        self._is_running = False
        self.last_signal: Optional[Signal] = None

        # Configuration from environment with defaults - enabled by default
        self.enabled = os.getenv('CMC_SCREENER_ENABLED', 'true').lower() == 'true'

        # Only create logger if enabled
        if self.enabled:
            self.logger = EnhancedLogger(f"CMCScreener_{self.symbol.value}")
        else:
            # Create a mock logger that doesn't log anything when disabled
            class MockLogger:
                def info(self, msg): pass
                def debug(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
                def critical(self, msg): pass
            self.logger = MockLogger()

        # Set screen_all flag if dealing with market-wide analysis
        self.screen_all = symbol in ["USDTUSDT", "MARKET"]

        # Load CMC API configuration from environment
        load_dotenv()
        self.cmc_api_key = os.getenv("CMC_API_KEY")
        if not self.cmc_api_key and self.enabled:
            self.logger.warning("CMC_API_KEY not found in environment variables. CMCScreener will not function "
                                "without it.")

        self.cmc_api_url = os.getenv("CMC_QUOTES_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest")
        self.cmc_listings_url = os.getenv("CMC_LISTINGS_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

        # Advanced API Rate Limiting with Circuit Breaker (from environment for configurability)
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_time = None
        self.failed_requests_count = 0
        self.max_failed_requests = int(os.getenv("CMC_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))  # Configurable failure threshold
        self.circuit_reset_timeout = int(os.getenv("CMC_CIRCUIT_BREAKER_RESET_TIMEOUT", "600"))  # 10 minutes default

        # API Call Throttling Controls (conservative for API conservation - loaded from env vars)
        self.api_call_interval = float(os.getenv("CMC_API_CALL_INTERVAL", "4.0"))  # 4-second min interval (very conservative for basic tier)
        self.max_calls_per_minute = int(os.getenv("CMC_MAX_CALLS_PER_MINUTE", "15"))  # 15/min for basic tier safety
        self.max_calls_per_hour = int(os.getenv("CMC_MAX_CALLS_PER_HOUR", "300")) # 300/hr for monthly quota conservation
        self.calls_this_minute = 0
        self.calls_this_hour = 0
        self.minute_start_time = time.time()
        self.hour_start_time = time.time()
        self.requests_lock = Lock()  # Thread-safe request counting

        # Enhanced Caching with Configurable TTLs from Environment - ENFORCED LOW UPDATE FREQUENCY
        self.cache_ttl = int(os.getenv("CMC_CACHE_TTL_SECONDS", "1800"))  # 30 minutes (very low update frequency)
        self.long_term_cache_ttl = int(os.getenv("CMC_LONG_TERM_CACHE_TTL_SECONDS", "3600"))  # 1 hour default
        self.cache = {}
        self.cache_times = {}

        # Separate cache for different data types with configurable TTL from environment
        self.quotes_cache_ttl = int(os.getenv("CMC_QUOTE_CACHE_TTL_SECONDS", "1800"))    # 30 minutes for live quotes
        self.listings_cache_ttl = int(os.getenv("CMC_LISTINGS_CACHE_TTL_SECONDS", "3600"))  # 1 hour for listings
        self.quotes_cache = {}
        self.listings_cache = {}
        self.quotes_cache_times = {}
        self.listings_cache_times = {}

        # Request queuing system for managing API demand during high load
        self.request_queue = []
        self.max_queue_size = 30  # Limit queue to prevent memory issues

        # Operation limiting configuration (for top coins screening) - VERY LOW FREQUENCY
        self.screen_top_coins_interval_hours = int(os.getenv("CMC_SCREEN_TOP_COINS_INTERVAL_HOURS", "6"))  # Every 6 hours
        self.screen_top_coins_limit = int(os.getenv("CMC_SCREEN_TOP_COINS_LIMIT", "20"))  # Max coins to screen
        self.max_coins_to_analyze_per_run = int(os.getenv("CMC_MAX_COINS_TO_ANALYZE_PER_RUN", "10"))  # Max per analysis run

        # Load excluded coins from environment
        excluded_coins_str = os.getenv("CMC_EXCLUDED_COINS", "BTC,ETH,SOL,ADA,DOT,XRP,DOGE,LINK,BNB,AVAX,MATIC")
        self.excluded_coins = set(coin.strip().upper() for coin in excluded_coins_str.split(',') if coin.strip())

        # Data storage for screening
        self.coins_data: Dict[str, Dict] = {}
        self.screening_results: Dict[str, Dict] = {}

        # Stablecoin detection
        self.stablecoin_tags = ['stablecoin', 'asset-backed-stablecoin', 'algorithmic-stablecoin']
        self.stablecoin_symbols = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FRAX', 'PYUSD', 'GUSD', 'USDD', 'EURT', 'UST', 'FEI', 'TRIBE']

        # Filters for growth/crash detection - adjusted for universe selection
        self.universe_filters = {
            'min_24h_change': 5.0,  # Reduced threshold for universe signals
            'min_volume_24h': 5_000_000,  # Higher volume threshold for quality
            'max_market_cap': 1_000_000_000,  # Higher max market cap
            'min_market_cap': 10_000_000,  # Higher min market cap
            'use_ma_filters': True
        }

        # Historical data for trend analysis
        self.price_history = {}
        self.volume_history = {}
        self.max_history_size = 100

        # Configuration for spike detection
        self.volume_spike_threshold = 2.0
        self.volatility_threshold = 0.05
        self.trend_confirmation_periods = 3

    def _rate_limit_check(self):
        """Advanced API rate limiting with circuit breaker and throttling for maximum conservation."""
        current_time = time.time()

        # Check circuit breaker status first
        if hasattr(self, 'circuit_breaker_open') and self.circuit_breaker_open:
            if current_time >= getattr(self, 'circuit_breaker_reset_time', 0):
                # Time to retry, reset circuit
                self.circuit_breaker_open = False
                self.failed_requests_count = 0
                self.logger.info("Circuit breaker reset, resuming API calls")
            else:
                # Circuit is still open, raise exception
                raise ConnectionError("Circuit breaker open due to API failures, try again later")

        # Ensure proper initialization of hour tracking
        if not hasattr(self, 'hour_start_time'):
            self.hour_start_time = current_time

        # Check and reset minute/hour counters with thread safety
        with self.requests_lock:
            # Reset minute counter
            if current_time - self.minute_start_time > 60:
                self.calls_this_minute = 0
                self.minute_start_time = current_time

            # Reset hour counter
            if current_time - self.hour_start_time > 3600:
                self.calls_this_hour = 0
                self.hour_start_time = current_time

            # Check minute limit
            if self.calls_this_minute >= self.max_calls_per_minute:
                sleep_time = 60 - (current_time - self.minute_start_time)
                if sleep_time > 0:
                    self.logger.info(f"Approaching minute limit ({self.calls_this_minute}/{self.max_calls_per_minute}), sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    self.calls_this_minute = 0
                    self.minute_start_time = current_time

            # Check hour limit for monthly quota conservation
            if self.calls_this_hour >= self.max_calls_per_hour:
                sleep_time = 3600 - (current_time - self.hour_start_time)
                if sleep_time > 0:
                    self.logger.info(f"Hourly limit reached ({self.calls_this_hour}/{self.max_calls_per_hour}), sleeping for {sleep_time:.2f}s to conserve monthly quota")
                    time.sleep(sleep_time)
                    self.calls_this_hour = 0
                    self.hour_start_time = current_time

        # Enforce interval between calls
        time_since_last_call = current_time - getattr(self, 'last_api_call_time', 0)
        if time_since_last_call < self.api_call_interval:
            sleep_time = self.api_call_interval - time_since_last_call
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Increment counters with thread safety
        with self.requests_lock:
            self.calls_this_minute += 1
            self.calls_this_hour += 1
        setattr(self, 'last_api_call_time', current_time)

    def _handle_api_failure(self):
        """Handle an API failure, potentially opening circuit breaker."""
        with self.requests_lock:
            self.failed_requests_count = getattr(self, 'failed_requests_count', 0) + 1
            if self.failed_requests_count >= getattr(self, 'max_failed_requests', 3):  # Use configurable threshold
                self.circuit_breaker_open = True
                self.circuit_breaker_reset_time = time.time() + getattr(self, 'circuit_reset_timeout', 600)  # Use configurable timeout
                self.logger.warning(f"Circuit breaker opened after {self.failed_requests_count} consecutive failures")

    def _handle_api_success(self):
        """Reset failure counter when API call succeeds."""
        with self.requests_lock:
            self.failed_requests_count = 0
            if hasattr(self, 'circuit_breaker_open') and self.circuit_breaker_open:
                self.logger.info("Circuit breaker closed, API operations resumed")
                self.circuit_breaker_open = False

    def _get_cache_key(self, symbol: str, data_type: str = "quote") -> str:
        """Generate a cache key for different types of data."""
        return f"{data_type}:{symbol.upper()}"

    def _is_cache_valid(self, cache_key: str, ttl: int = None) -> bool:
        """Check if cached data is still valid based on TTL."""
        if cache_key not in self.cache_times:
            return False

        ttl = ttl or self.cache_ttl
        cache_age = datetime.now() - self.cache_times[cache_key]
        return cache_age.total_seconds() < ttl

    def _get_from_cache(self, symbol: str, data_type: str = "quote") -> Optional[Dict[str, Any]]:
        """Retrieve data from cache if valid."""
        cache_key = self._get_cache_key(symbol, data_type)

        # Determine which cache to use based on data type
        cache_to_use = self.listings_cache if data_type == "listings" else self.quotes_cache
        cache_times_to_use = self.listings_cache_times if data_type == "listings" else self.quotes_cache_times

        # Check if cache exists and is valid
        if (
            cache_key in cache_to_use and
            cache_key in cache_times_to_use and
            (datetime.now() - cache_times_to_use[cache_key]).total_seconds() < (
                self.listings_cache_ttl if data_type == "listings" else self.quotes_cache_ttl
            )
        ):
            return cache_to_use[cache_key]

        return None

    def _store_in_cache(self, symbol: str, data: Any, data_type: str = "quote"):
        """Store data in cache with timestamp."""
        cache_key = self._get_cache_key(symbol, data_type)

        # Determine which cache to use based on data type
        cache_to_use = self.listings_cache if data_type == "listings" else self.quotes_cache
        cache_times_to_use = self.listings_cache_times if data_type == "listings" else self.quotes_cache_times
        ttl_to_use = self.listings_cache_ttl if data_type == "listings" else self.quotes_cache_ttl

        # Only store if data is not None
        if data is not None:
            cache_to_use[cache_key] = data
            cache_times_to_use[cache_key] = datetime.now()

    def _update_with_market_data(self, data: Dict[str, Any]):
        """Update the screener with new market data."""
        # CMC screener primarily fetches data from external API
        # This method is kept for interface compatibility
        pass

    def _is_general_cache_valid(self, cache_key: str) -> bool:
        """Check if general cache data is still valid."""
        if cache_key not in self.cache_times:
            return False
        cache_age = datetime.now() - self.cache_times[cache_key]
        return cache_age.total_seconds() < self.cache_ttl

    def _store_in_general_cache(self, cache_key: str, data: Any):
        """Store data in general cache with timestamp."""
        self.cache[cache_key] = data
        self.cache_times[cache_key] = datetime.now()

    def _get_from_general_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from general cache if valid."""
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        return None

    def _extract_base_symbol(self, symbol: str) -> str:
        """Extract the base cryptocurrency symbol from various formats."""
        # Handle symbols like BTCUSDT, etc.
        if len(symbol) > 3 and symbol.endswith(('USDT', 'USD', 'BTC', 'ETH', 'BNB')):
            quote_parts = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP', 'USDC']
            for part in quote_parts:
                if symbol.endswith(part):
                    return symbol[:-len(part)]
            return symbol[:3] if len(symbol) > 6 else symbol[:6]
        else:
            # For simple symbols like BTC, return as is (max 5 chars to be safe)
            return symbol[:5]

    def is_coin_excluded(self, coin_data: Dict) -> bool:
        """Check if a coin should be excluded based on our exclusion list."""
        symbol = coin_data.get('symbol', '').upper()
        return symbol in self.excluded_coins

    def _is_stablecoin(self, coin_data: Dict[str, Any]) -> bool:
        """Check if a coin is a stablecoin using multiple criteria."""
        symbol = coin_data.get('symbol', '')
        price = coin_data.get('price', 0)
        tags = coin_data.get('tags', [])

        # Known stablecoin symbols
        stablecoin_symbols = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FRAX', 'PYUSD', 'GUSD', 'USDD', 'EURT', 'UST', 'FEI', 'TRIBE']

        # Tag-based filter
        stablecoin_tags = ['stablecoin', 'asset-backed-stablecoin', 'algorithmic-stablecoin']
        for tag in stablecoin_tags:
            if tag in tags:
                return True

        # Price-based filter (around $1)
        if 0.95 < price < 1.05:
            return True

        # Known stablecoin blacklist
        if symbol in stablecoin_symbols:
            return True

        return False

    def fetch_cmc_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch cryptocurrency data from CoinMarketCap API with caching and rate limiting."""
        base_symbol = self._extract_base_symbol(symbol)
        cache_key = self._get_cache_key(base_symbol, "quote")

        # Check cache first
        cached_data = self._get_from_cache(base_symbol, "quote")
        if cached_data:
            return cached_data

        self._rate_limit_check()

        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
        }

        params = {'symbol': base_symbol}

        try:
            response = requests.get(self.cmc_api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                crypto_data = list(data['data'].values())[0] if isinstance(data['data'], dict) else data['data'][0]

                if crypto_data:
                    quote = crypto_data.get('quote', {}).get('USD', {})

                    result = {
                        'symbol': crypto_data.get('symbol'),
                        'name': crypto_data.get('name'),
                        'rank': crypto_data.get('cmc_rank', 0),
                        'price': quote.get('price', 0),
                        'market_cap': quote.get('market_cap', 0),
                        'volume_24h': quote.get('volume_24h', 0),
                        'percent_change_1h': quote.get('percent_change_1h', 0),
                        'percent_change_24h': quote.get('percent_change_24h', 0),
                        'percent_change_7d': quote.get('percent_change_7d', 0),
                        'last_updated': quote.get('last_updated'),
                        'tags': crypto_data.get('tags', []),
                        'circulating_supply': crypto_data.get('circulating_supply', 0),
                        'total_supply': crypto_data.get('total_supply', 0),
                        'max_supply': crypto_data.get('max_supply', 0),
                    }

                    # Store in cache
                    self._store_in_cache(base_symbol, result, "quote")
                    return result
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching CMC data for {symbol}: {e}")
            self._handle_api_failure()  # Handle API failure
        except Exception as e:
            self.logger.error(f"Error processing CMC data for {symbol}: {e}")
            self._handle_api_failure()  # Handle any other error

        return None

    def fetch_top_cryptocurrencies(self, limit: int = None) -> Optional[List[Dict]]:
        """Fetch top cryptocurrencies from CMC listings API with caching and rate limiting."""
        # Use the configured limit from environment if not specified
        if limit is None:
            limit = self.screen_top_coins_limit

        # Ensure we don't exceed the configured limit
        limit = min(limit, self.screen_top_coins_limit)

        cache_key = self._get_cache_key(f"top_{limit}", "listings")

        # Check cache first for listings
        cached_data = self._get_from_cache(f"top_{limit}", "listings")
        if cached_data:
            return cached_data

        self._rate_limit_check()

        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
        }

        params = {
            'start': '1',
            'limit': str(limit),
            'convert': 'USD'
        }

        try:
            response = requests.get(self.cmc_listings_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if 'data' in data:
                result = data['data']

                # Store in listings cache
                self._store_in_cache(f"top_{limit}", result, "listings")
                return result
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching CMC listings: {e}")
            self._handle_api_failure()  # Handle API failure
        except Exception as e:
            self.logger.error(f"Error processing CMC listings: {e}")
            self._handle_api_failure()  # Handle any other error

        return None

    def check_growth_potential(self, coin_data: Dict) -> Tuple[bool, List[str]]:
        """Check if a coin qualifies as high-growth potential."""
        reasons = []
        is_growth = True

        # Check 24h change > min change threshold
        change_24h = coin_data.get('percent_change_24h', 0)
        min_change = self.growth_filters['min_24h_change']
        if change_24h > min_change:
            reasons.append(f"24h change {change_24h:.2f}% > {min_change}%")
        else:
            is_growth = False
            reasons.append(f"24h change {change_24h:.2f}% <= {min_change}%")

        # Check volume
        volume_24h = coin_data.get('volume_24h', 0)
        min_volume = self.growth_filters['min_volume_24h']
        if volume_24h > min_volume:
            reasons.append(f"Volume {volume_24h:,.0f} > {min_volume:,}")
        else:
            is_growth = False
            reasons.append(f"Volume {volume_24h:,.0f} <= {min_volume:,}")

        # Check market cap range
        market_cap = coin_data.get('market_cap', 0)
        max_market_cap = self.growth_filters['max_market_cap']
        min_market_cap = self.growth_filters['min_market_cap']
        if market_cap <= max_market_cap and market_cap > min_market_cap:
            reasons.append(f"Market cap {market_cap:,.0f} in range ({min_market_cap:,}, {max_market_cap:,}]")
        else:
            is_growth = False
            reasons.append(f"Market cap {market_cap:,.0f} outside range ({min_market_cap:,}, {max_market_cap:,}]")

        return is_growth, reasons

    def check_crash_risk(self, coin_data: Dict) -> Tuple[bool, List[str]]:
        """Check if a coin qualifies as high-crash risk."""
        reasons = []
        is_crash_risk = True

        # Check 24h change < -threshold (more conservative)
        change_24h = coin_data.get('percent_change_24h', 0)
        max_change = -8.0
        if change_24h < max_change:
            reasons.append(f"24h change {change_24h:.2f}% < {max_change}%")
        else:
            is_crash_risk = False
            reasons.append(f"24h change {change_24h:.2f}% >= {max_change}%")

        # Check volume
        volume_24h = coin_data.get('volume_24h', 0)
        min_volume = 1_000_000
        if volume_24h > min_volume:
            reasons.append(f"Volume {volume_24h:,.0f} > {min_volume:,}")
        else:
            is_crash_risk = False
            reasons.append(f"Volume {volume_24h:,.0f} <= {min_volume:,}")

        return is_crash_risk, reasons

    def _add_to_coin_history(self, symbol: str, price: float, volume: float):
        """Add price and volume data to history for trend analysis."""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.max_history_size)
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=self.max_history_size)

        self.price_history[symbol].append((datetime.now(), price))
        self.volume_history[symbol].append((datetime.now(), volume))

    def _calculate_volume_surges(self, symbol: str, current_volume: float) -> float:
        """Calculate volume surge score compared to historical volume."""
        if symbol not in self.volume_history or len(self.volume_history[symbol]) < 10:
            return 0.0  # Not enough history to calculate

        # Calculate average volume from history
        historical_volumes = [vol for _, vol in list(self.volume_history[symbol])[-20:]]  # Last 20 readings
        if not historical_volumes:
            return 0.0

        avg_volume = sum(historical_volumes) / len(historical_volumes)
        if avg_volume == 0:
            return 0.0

        # Calculate surge factor
        surge_factor = current_volume / avg_volume if avg_volume > 0 else 0
        # Normalize to 0-1 range, with diminishing returns for very high surges
        surge_score = min(1.0, (surge_factor - 1.0) / 5.0) if surge_factor > 1.0 else 0.0

        return surge_score

    def _calculate_momentum_score(self, change_24h: float, change_1h: float, change_7d: float) -> float:
        """Calculate a normalized momentum score based on multiple timeframes."""
        # Weighted momentum calculation with multiple timeframes
        momentum = (
            (change_24h / 100.0) * 0.3 +    # 24h change (30% weight)
            (change_1h / 100.0) * 0.5 +     # 1h change (50% weight) 
            (change_7d / 100.0) * 0.2       # 7d change (20% weight)
        )
        
        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, momentum))

    def _analyze_multi_timeframe_trend(self, change_1h: float, change_24h: float, change_7d: float, change_30d: float = 0.0) -> Tuple[SignalType, float]:
        """Analyze trend across multiple timeframes."""
        # Calculate trend consistency score
        positive_trend = sum(x > 0 for x in [change_1h, change_24h, change_7d, change_30d])
        negative_trend = sum(x < 0 for x in [change_1h, change_24h, change_7d, change_30d])
        
        # Determine dominant trend
        if positive_trend >= 2:  # At least 2/4 timeframes are positive
            signal_type = SignalType.BUY
            confidence = 0.4 + (positive_trend / 4.0) * 0.5  # 40-90% confidence based on consistency
        elif negative_trend >= 2:  # At least 2/4 timeframes are negative
            signal_type = SignalType.SELL 
            confidence = 0.4 + (negative_trend / 4.0) * 0.5  # 40-90% confidence based on consistency
        else:
            signal_type = SignalType.NEUTRAL
            confidence = 0.3  # Lower confidence for mixed signals

        return signal_type, confidence

    def _detect_volume_spike_statistical(self, symbol: str, current_volume: float) -> bool:
        """Use statistical methods to detect volume spikes."""
        if symbol not in self.volume_history or len(self.volume_history[symbol]) < 5:
            return False  # Not enough history

        # Get historical volumes
        historical_volumes = [vol for _, vol in list(self.volume_history[symbol])[-20:]]
        if len(historical_volumes) < 5:
            return False

        # Calculate statistical measures
        mean_vol = sum(historical_volumes) / len(historical_volumes)
        variance = sum((x - mean_vol) ** 2 for x in historical_volumes) / len(historical_volumes)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return current_volume > mean_vol * self.volume_spike_threshold  # Simple threshold check

        # If volume is more than 2 standard deviations above mean, it's a spike
        return (current_volume - mean_vol) / std_dev > 2.0

    def _categorize_market_cap(self, market_cap: float) -> str:
        """Categorize market cap size."""
        if market_cap >= 10_000_000_000:  # $10B+
            return 'large'
        elif market_cap >= 1_000_000_000:  # $1B-$10B
            return 'medium'
        elif market_cap >= 100_000_000:   # $100M-$1B
            return 'small'
        elif market_cap >= 10_000_000:    # $10M-$100M
            return 'micro'
        else:                             # <$10M
            return 'nano'

    def _enhanced_analyze_individual_coin(self, symbol: Symbol, cmc_data: Dict[str, Any]) -> Optional[Signal]:
        """Enhanced individual coin analysis with multiple metrics."""
        from datetime import datetime

        # Check if the coin is a stablecoin (should be excluded)
        if self._is_stablecoin(cmc_data):
            return None

        # Get all available metrics
        percent_change_24h = cmc_data.get('percent_change_24h', 0)
        percent_change_1h = cmc_data.get('percent_change_1h', 0)
        percent_change_7d = cmc_data.get('percent_change_7d', 0)
        volume_24h = cmc_data.get('volume_24h', 0)
        market_cap = cmc_data.get('market_cap', 0)
        price = cmc_data.get('price', 0)
        rank = cmc_data.get('rank', 99999)

        # Add to history for trend analysis
        if price > 0:
            self._add_to_coin_history(self._extract_base_symbol(symbol.value), price, volume_24h)

        # Calculate additional metrics
        volatility_24h = abs(percent_change_24h) / 100  # Convert to decimal
        volume_surge_score = 0.0  # Placeholder - would implement in a full version
        momentum_score = (percent_change_24h + percent_change_1h * 2 + percent_change_7d * 0.5) / 300.0  # Simplified momentum

        # Determine trend signal based on multiple timeframes
        if percent_change_1h > 0 and percent_change_24h > 0:
            trend_signal = SignalType.BUY
            trend_confidence = 0.6
        elif percent_change_1h < 0 and percent_change_24h < 0:
            trend_signal = SignalType.SELL
            trend_confidence = 0.6
        else:
            trend_signal = SignalType.NEUTRAL
            trend_confidence = 0.3

        # Volume spike detection (simplified)
        is_volume_spike = volume_24h > (market_cap * 0.001)  # If volume > 0.1% of market cap, consider it a spike

        # Market cap consideration (smaller caps can be more volatile and risky)
        market_cap_category = self._categorize_market_cap(market_cap)

        # Determine signal type based on comprehensive analysis
        final_signal_type = None
        final_confidence = Decimal('0.5')
        final_score = 0.0

        # Strong buy signals
        if trend_signal == SignalType.BUY and momentum_score > 0.007 and is_volume_spike:  # Adjusted momentum threshold
            final_signal_type = SignalType.BUY
            final_confidence = Decimal('0.9')
            final_score = min(1.0, momentum_score * 120.0)  # Adjust for simplified momentum scale
        elif trend_signal == SignalType.BUY and momentum_score > 0.005 and volatility_24h > self.volatility_threshold:
            final_signal_type = SignalType.BUY
            final_confidence = Decimal('0.75')
            final_score = min(0.9, momentum_score * 100.0)
        elif percent_change_1h > 5 and volume_24h > 1000000:  # Short-term momentum with volume
            final_signal_type = SignalType.BUY
            final_confidence = Decimal('0.7')
            final_score = min(0.8, percent_change_1h / 100.0)

        # Strong sell signals
        elif trend_signal == SignalType.SELL and momentum_score < -0.007 and is_volume_spike:  # Adjusted momentum threshold
            final_signal_type = SignalType.SELL
            final_confidence = Decimal('0.9')
            final_score = max(-1.0, momentum_score * 120.0)  # Adjust for simplified momentum scale
        elif trend_signal == SignalType.SELL and momentum_score < -0.005 and volatility_24h > self.volatility_threshold:
            final_signal_type = SignalType.SELL
            final_confidence = Decimal('0.75')
            final_score = max(-0.9, momentum_score * 100.0)
        elif percent_change_1h < -5 and volume_24h > 1000000:  # Short-term decline with volume
            final_signal_type = SignalType.SELL
            final_confidence = Decimal('0.7')
            final_score = max(-0.8, percent_change_1h / 100.0)

        # Hold signals for high volatility or uncertain conditions
        elif abs(percent_change_24h) < 3 and abs(percent_change_1h) < 2:  # Low volatility, likely sideways action
            final_signal_type = SignalType.HOLD
            final_confidence = Decimal('0.4')
            final_score = 0.0
        elif volatility_24h > 0.15:  # Very high volatility, might be risky
            final_signal_type = SignalType.HOLD
            final_confidence = Decimal('0.6')
            final_score = momentum_score * 50.0  # Reduce impact of momentum in high vol
        else:  # Neutral market
            final_signal_type = SignalType.NEUTRAL
            final_confidence = Decimal('0.5')
            final_score = momentum_score * 70.0  # Reduce impact for neutral signal

        # Adjust confidence based on market cap (smaller caps have higher uncertainty)
        if market_cap_category in ['small', 'micro', 'nano']:
            final_confidence = final_confidence * Decimal('0.8')  # Reduce confidence for smaller caps

        # Ensure final_score is within valid range [-1.0, 1.0]
        final_score = max(-1.0, min(1.0, final_score))

        # Create and return signal
        signal = Signal(
            symbol=symbol,
            signal_type=final_signal_type,
            confidence=Percentage(final_confidence),
            score=final_score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="CMCScreener",
            metadata={
                'cmc_data': cmc_data,
                'percent_change_24h': percent_change_24h,
                'percent_change_1h': percent_change_1h,
                'percent_change_7d': percent_change_7d,
                'volume_24h': volume_24h,
                'market_cap': market_cap,
                'price': price,
                'rank': rank,
                'volatility_24h': volatility_24h,
                'volume_surge_score': volume_surge_score,
                'momentum_score': momentum_score,
                'trend_signal': trend_signal.name if trend_signal else 'NONE',
                'trend_confidence': trend_confidence,
                'is_volume_spike': is_volume_spike,
                'market_cap_category': market_cap_category,
                'analysis_type': 'enhanced_cmc_analysis'
            }
        )

        return signal

    def _analyze_realistic_scalping_signals(self, symbol: Symbol, cmc_data: Dict[str, Any]) -> Optional[Signal]:
        """Analyze realistic scalping-specific signals using sophisticated indicators."""
        from datetime import datetime

        # Extract available data
        price = cmc_data.get('price', 0)
        high = cmc_data.get('high', price * 1.01)  # Use a proxy if not available
        low = cmc_data.get('low', price * 0.99)    # Use a proxy if not available
        close = cmc_data.get('price', price)       # Current price as close
        volume_24h = cmc_data.get('volume_24h', 0)
        change_1h = cmc_data.get('percent_change_1h', 0)
        change_24h = cmc_data.get('percent_change_24h', 0)
        change_7d = cmc_data.get('percent_change_7d', 0)

        # Calculate volatility levels for scalping (higher volatility indicates more scalping opportunities)
        volatility_1h = abs(change_1h) / 100.0
        volatility_24h = abs(change_24h) / 100.0
        average_volatility = (volatility_1h + volatility_24h) / 2.0

        # Check if coin meets scalping prerequisites (enough liquidity)
        min_liquidity = getattr(self, 'scalping_liquidity_threshold', 5_000_000)
        if volume_24h < min_liquidity:
            # Not enough liquidity for reliable scalping
            return None

        # Microstructure analysis (simplified but realistic)
        microstructure = self._analyze_microstructure(high, low, close, volume_24h,
                                                    high * 0.998, low * 1.002, close * 0.999)  # Simulated previous values

        # Scalping opportunity analysis with realistic parameters
        opportunity_score = 0.0
        signal_type = SignalType.NEUTRAL

        # Primary scalping opportunities based on volatility and momentum patterns
        scalping_volatility_threshold = getattr(self, 'scalping_volatility_threshold', 0.025)  # 2.5% average volatility
        if average_volatility > scalping_volatility_threshold:
            # High volatility creates scalping opportunities
            opportunity_score += 0.25

            # Look for momentum exhaustion patterns (potential reversals)
            if change_1h > 3.0 and volatility_1h > 0.04:  # Strong move with high volatility = potential reversal
                signal_type = SignalType.SELL  # Potential for pullback/fade to downside
                opportunity_score += 0.2
            elif change_1h < -3.0 and volatility_1h > 0.04:  # Strong decline with high volatility = potential bounce
                signal_type = SignalType.BUY   # Potential for recovery/bounce to upside
                opportunity_score += 0.2
            elif abs(change_1h) > 1.8 and abs(change_1h - change_24h) > 1.2:  # Divergence between short and medium-term trends
                # This suggests momentum is changing
                if change_1h > 0 and change_24h < 0:  # Short term positive, long term negative = possible reversal down
                    signal_type = SignalType.SELL
                    opportunity_score += 0.15
                elif change_1h < 0 and change_24h > 0:  # Short term negative, long term positive = possible reversal up
                    signal_type = SignalType.BUY
                    opportunity_score += 0.15

        # Secondary signals based on price positioning and market structure
        # Look for range extremes that indicate potential mean reversion opportunities
        if microstructure['price_position'] > 0.85:  # Very near high of range
            signal_type = SignalType.SELL
            opportunity_score += 0.12
        elif microstructure['price_position'] < 0.15:  # Very near low of range
            signal_type = SignalType.BUY
            opportunity_score += 0.12

        # Look for pattern-based signals (engulfing, hammer-like patterns)
        if microstructure['bullish_engulfing'] > 0.5:
            if signal_type != SignalType.SELL:  # Don't override stronger signals
                signal_type = SignalType.BUY
            opportunity_score += 0.1
        elif microstructure['bearish_engulfing'] > 0.5:
            if signal_type != SignalType.BUY:
                signal_type = SignalType.SELL
            opportunity_score += 0.1

        if microstructure['inverted_hammer'] > 0.7 and microstructure['price_position'] < 0.2:
            # Potential bullish reversal at bottom of range (strong signal)
            if signal_type != SignalType.SELL:
                signal_type = SignalType.BUY
            opportunity_score += 0.15
        elif microstructure['shooting_star'] > 0.7 and microstructure['price_position'] > 0.8:
            # Potential bearish reversal at top of range (strong signal)
            if signal_type != SignalType.BUY:
                signal_type = SignalType.SELL
            opportunity_score += 0.15

        # Additional checks for market structure and trend quality
        if change_7d > 12 and change_1h < -2.5:  # Longer term bullish trend but short term correction
            if signal_type == SignalType.NEUTRAL:
                signal_type = SignalType.BUY  # Potential dip buying in bullish trend
                opportunity_score += 0.08
        elif change_7d < -12 and change_1h > 2.5:  # Longer term bearish trend but short term bounce
            if signal_type == SignalType.NEUTRAL:
                signal_type = SignalType.SELL  # Potential rally selling in bearish trend
                opportunity_score += 0.08

        # Adjust confidence based on opportunity score
        if opportunity_score > 0.15:  # Only generate signals for meaningful opportunities
            base_confidence = Decimal('0.5')
            # Amplify confidence for higher opportunity scores
            additional_confidence = min(Decimal('0.4'), Decimal(str(opportunity_score * 1.6)))
            confidence = Percentage(base_confidence + additional_confidence)
            score = max(-1.0, min(1.0, opportunity_score * 1.4))  # Slightly amplify the score, clamp to [-1.0, 1.0]
        else:
            return None  # No significant scalping opportunity

        # Create and return scalping signal
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=f"{self.name}_Realistic_Scalping",
            timestamp=datetime.now(),
            source_engine="CMCScreener_Realistic_Scalping",
            metadata={
                'cmc_data': cmc_data,
                'volatility_1h': volatility_1h,
                'volatility_24h': volatility_24h,
                'average_volatility': average_volatility,
                'volume_24h': volume_24h,
                'microstructure_analysis': microstructure,
                'scalping_score': opportunity_score,
                'analysis_type': 'realistic_scalping_analysis',
                'timeframe_analysis': {
                    '1h_change': change_1h,
                    '24h_change': change_24h,
                    '7d_change': change_7d
                },
                'scalping_conditions': {
                    'high_volatility': average_volatility > scalping_volatility_threshold,
                    'sufficient_liquidity': volume_24h >= min_liquidity
                }
            }
        )

        return signal

    def _adjust_signal_for_scalping(self, original_signal: Signal) -> Signal:
        """Adjust a signal to be more suitable for scalping with appropriate risk settings."""
        # For scalping, we modify the signal characteristics:
        # 1. Potentially adjust confidence as scalping is more speculative in nature
        # 2. Add scalping-specific metadata
        # 3. Adjust risk/position sizing parameters for faster turnover

        original_conf = float(original_signal.confidence.value)
        # Slightly reduce confidence for scalping (as short-term signals can be noisier)
        adjusted_confidence = Percentage(Decimal(str(min(0.9, original_conf * 0.85))))

        # Create new signal with scalping modifications
        from datetime import datetime
        scalping_signal = Signal(
            symbol=original_signal.symbol,
            signal_type=original_signal.signal_type,
            confidence=adjusted_confidence,
            score=original_signal.score,
            strategy_name=f"{original_signal.strategy_name}_Scalping",
            timestamp=datetime.now(),
            source_engine="CMCScreener_Scalping_Adjusted",
            metadata={
                **original_signal.metadata,
                'scalping_adjustment_applied': True,
                'target_profit_points': 0.0025,  # 0.25% typical scalping target
                'stop_loss_points': 0.0035,      # 0.35% typical scalping protection
                'execution_speed': 'high',       # Indicate this is for fast execution
                'timeframe_target': '1m-15m'     # Target timeframe for scalping
            }
        )

        return scalping_signal

    def _add_to_coin_history(self, symbol: str, price: float, volume: float):
        """Add current pricing/volume data to history for trend analysis."""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.max_history_size)
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=self.max_history_size)

        # Add (timestamp, value) tuples to history
        self.price_history[symbol].append((datetime.now(), price))
        self.volume_history[symbol].append((datetime.now(), volume))

    def _categorize_market_cap(self, market_cap: float) -> str:
        """Categorize market cap size."""
        if market_cap >= 10_000_000_000:  # $10B+
            return 'large'
        elif market_cap >= 1_000_000_000:  # $1B-$10B
            return 'medium'
        elif market_cap >= 100_000_000:   # $100M-$1B
            return 'small'
        elif market_cap >= 10_000_000:    # $10M-$100M
            return 'micro'
        else:                             # <$10M
            return 'nano'

    def screen_coins(self, limit: int = 100) -> Dict[str, Dict]:
        """Screen top coins to identify growth and crash risk opportunities."""
        self.logger.info(f"Starting screening of top {limit} coins...")

        top_coins = self.fetch_top_cryptocurrencies(limit=limit)
        if not top_coins:
            self.logger.warning("Could not fetch top cryptocurrencies for screening")
            return {}

        screening_results = {}
        total_analyzed = 0
        growth_count = 0
        crash_count = 0

        for coin in top_coins:
            # Respect the max coins to analyze per run limit
            if total_analyzed >= self.max_coins_to_analyze_per_run:
                self.logger.info(f"Reached maximum coins to analyze per run limit ({self.max_coins_to_analyze_per_run})")
                break

            coin_symbol = coin.get('symbol', '').upper()

            # Skip excluded coins
            if coin_symbol in self.excluded_coins:
                continue

            # Create coin data dictionary
            coin_data = {
                'symbol': coin.get('symbol', ''),
                'name': coin.get('name', ''),
                'rank': coin.get('cmc_rank', 0),
                'price': coin.get('quote', {}).get('USD', {}).get('price', 0),
                'market_cap': coin.get('quote', {}).get('USD', {}).get('market_cap', 0),
                'volume_24h': coin.get('quote', {}).get('USD', {}).get('volume_24h', 0),
                'percent_change_1h': coin.get('quote', {}).get('USD', {}).get('percent_change_1h', 0),
                'percent_change_24h': coin.get('quote', {}).get('USD', {}).get('percent_change_24h', 0),
                'percent_change_7d': coin.get('quote', {}).get('USD', {}).get('percent_change_7d', 0),
                'tags': coin.get('tags', []),
            }

            # Skip if it's a stablecoin
            if self._is_stablecoin(coin_data):
                continue

            # Determine if this coin shows growth potential or crash risk
            is_growth, growth_reasons = self.check_growth_potential(coin_data)
            is_crash_risk, crash_reasons = self.check_crash_risk(coin_data)

            screening_results[coin_symbol] = {
                'name': coin_data['name'],
                'data': coin_data,
                'is_growth_potential': is_growth,
                'is_crash_risk': is_crash_risk,
                'growth_reasons': growth_reasons,
                'crash_reasons': crash_reasons,
                'enhanced_analysis': self._enhanced_analyze_individual_coin(Symbol(f"{coin_symbol}USDT"), coin_data)
            }

            if is_growth:
                growth_count += 1
            elif is_crash_risk:
                crash_count += 1

            total_analyzed += 1

            # Update coins_data and screening_results for tracking
            self.coins_data[coin_symbol] = coin_data
            self.screening_results[coin_symbol] = screening_results[coin_symbol]

        self.logger.info(f"Screening completed: {total_analyzed} coins analyzed, {growth_count} growth, {crash_count} crash-risk")

        return screening_results

    def _should_emit_signal(self, current_signal: Signal) -> bool:
        """Determine if a new signal should be emitted."""
        if not self.last_signal:
            return True

        # Don't emit if the same signal type was generated recently with similar confidence
        same_signal_type = current_signal.signal_type == self.last_signal.signal_type
        confidence_diff = abs(float(current_signal.confidence.value) - float(self.last_signal.confidence.value))

        return not (same_signal_type and confidence_diff < 0.1)

    def analyze(self, symbol: Symbol = None) -> Optional[Signal]:
        """Analyze market conditions and return a universe signal, NOT trade signal."""
        if not self.enabled:
            return None

        target_symbol = symbol or self.symbol

        # For comprehensive screening, run the screening process
        if target_symbol.value in ["USDTUSDT", "MARKET"] or self.screen_all:
            screening_results = self.screen_coins(limit=20)  # Reduced limit for low frequency

            # Count growth and crash risk coins for universe selection signal
            growth_coins = []
            crash_coins = []
            for symbol_key, data in screening_results.items():
                if data.get('is_growth_potential'):
                    growth_coins.append(data)
                if data.get('is_crash_risk'):
                    crash_coins.append(data)

            # Create universe signal based on screening results
            total_analyzed = len(growth_coins) + len(crash_coins)
            if total_analyzed > 0:
                growth_ratio = len(growth_coins) / total_analyzed
                crash_ratio = len(crash_coins) / total_analyzed

                # Generate universe signal, NOT trade signal
                signal_type = SignalType.HOLD  # Never emit BUY/SELL directly
                confidence = Percentage(Decimal('0.7'))  # High confidence in universe selection

                universe_signal = Signal(
                    symbol=Symbol("UNIVERSE"),
                    signal_type=signal_type,
                    confidence=confidence,
                    score=0.0,
                    strategy_name=f"{self.name}_Universe",
                    timestamp=datetime.now(),
                    source_engine="CMCScreener_Universe",
                    metadata={
                        'total_analyzed': total_analyzed,
                        'growth_count': len(growth_coins),
                        'crash_count': len(crash_coins),
                        'growth_ratio': growth_ratio,
                        'crash_ratio': crash_ratio,
                        'screening_type': 'universe_selection',
                        'selected_coins': [data['symbol'] for data in growth_coins[:5]],  # Top 5 growth coins
                        'explanation': f"Universe contains {len(growth_coins)} growth potential coins out of {total_analyzed} analyzed"
                    }
                )

                if self._should_emit_signal(universe_signal):
                    self.last_signal = universe_signal
                    return universe_signal

        else:
            # For specific symbol analysis - return universe signal only
            cmc_data = self.fetch_cmc_data(target_symbol.value)
            if not cmc_data:
                self.logger.warning(f"Could not fetch CMC data for {target_symbol.value}")
                self._handle_api_success()  # Still count successful call attempts
                return None

            # Skip if it's in the excluded list
            if self.is_coin_excluded(cmc_data):
                self.logger.info(f"Skipping excluded coin: {cmc_data['symbol']}")
                self._handle_api_success()  # Even excluded coins count as successful API use
                return None

            # Skip if it's a stablecoin
            if self._is_stablecoin(cmc_data):
                self.logger.info(f"Skipping stablecoin: {cmc_data['symbol']}")
                self._handle_api_success()  # Stablecoin checks still count as successful API use
                return None

            # Evaluate if this coin is suitable for universe inclusion
            is_suitable_for_universe = self._is_coin_suitable_for_universe(cmc_data)

            if is_suitable_for_universe:
                # Generate universe inclusion signal, NOT trade signal
                universe_signal = Signal(
                    symbol=target_symbol,
                    signal_type=SignalType.HOLD,  # Never emit BUY/SELL directly
                    confidence=Percentage(Decimal('0.6')),
                    score=0.0,
                    strategy_name=f"{self.name}_Universe_Inclusion",
                    timestamp=datetime.now(),
                    source_engine="CMCScreener_Universe",
                    metadata={
                        'coin_suitable_for_universe': True,
                        'symbol': cmc_data['symbol'],
                        'cmc_data_summary': {
                            'price': cmc_data.get('price'),
                            'volume_24h': cmc_data.get('volume_24h'),
                            'market_cap': cmc_data.get('market_cap'),
                            'change_24h': cmc_data.get('percent_change_24h'),
                        },
                        'screening_type': 'universe_inclusion',
                        'explanation': f"{cmc_data['symbol']} meets universe selection criteria"
                    }
                )

                if self._should_emit_signal(universe_signal):
                    self.last_signal = universe_signal
                    self.logger.info(f"{self.name} generated UNIVERSE-INCLUSION signal for {target_symbol.value}")
                    self._handle_api_success()  # Report successful API operation
                    return universe_signal

        self._handle_api_success()  # Report successful operation regardless of result
        return None

    def _is_coin_suitable_for_universe(self, cmc_data: Dict) -> bool:
        """Check if a coin is suitable for universe inclusion based on quality criteria"""
        # Check volume threshold
        volume_24h = cmc_data.get('volume_24h', 0)
        if volume_24h < self.universe_filters['min_volume_24h']:
            return False

        # Check market cap thresholds
        market_cap = cmc_data.get('market_cap', 0)
        if market_cap < self.universe_filters['min_market_cap'] or market_cap > self.universe_filters['max_market_cap']:
            return False

        # Check 24h change is not too extreme (to avoid very volatile coins)
        change_24h = abs(cmc_data.get('percent_change_24h', 0))
        if change_24h > 50:  # More than 50% change in 24h is too volatile
            return False

        return True

    def get_high_growth_coins(self) -> List[Dict]:
        """Get coins identified as high-growth potential"""
        high_growth_coins = []
        for symbol, data in self.screening_results.items():
            if data.get('is_growth_potential'):
                high_growth_coins.append({
                    'symbol': symbol,
                    'name': data['name'],
                    'data': data['data'],
                    'reasons': data['growth_reasons']
                })
        return high_growth_coins

    def get_high_crash_risk_coins(self) -> List[Dict]:
        """Get coins identified as high-crash risk"""
        high_crash_coins = []
        for symbol, data in self.screening_results.items():
            if data.get('is_crash_risk'):
                high_crash_coins.append({
                    'symbol': symbol,
                    'name': data['name'],
                    'data': data['data'],
                    'reasons': data['crash_reasons']
                })
        return high_crash_coins

    def start(self):
        """Start the CMC screener."""
        self._is_running = True
        self.logger.info(f"CMCScreener {self.name} started")

    def stop(self):
        """Stop the CMC screener."""
        self._is_running = False
        # Clear caches when stopping
        self.cache.clear()
        self.cache_times.clear()
        self.logger.info(f"CMCScreener {self.name} stopped")

    def update_data(self, data: Dict[str, Any]):
        """Update the screener with new market data."""
        # CMC screener primarily fetches data from external API
        # This method is kept for interface compatibility
        pass

    def is_running(self) -> bool:
        """Check if the screener is currently running."""
        return self._is_running

    def _calculate_vwap(self, df, lookback: int = 200) -> float:
        """Calculate VWAP for scalping reversals (simplified for single data point)."""
        # In a real implementation, this would calculate VWAP from historical OHLCV data
        # For now, we'll return a placeholder that would be computed from real data
        if not df or not isinstance(df, dict):
            return 0.0
        # This is a simplified example - actual VWAP calculation needs OHLCV data
        return df.get('price', 0)

    def _detect_vwap_reversal(self, price: float, vwap: float, distance_threshold: float = 0.005) -> Optional[SignalType]:
        """Detect VWAP-based reversal opportunities for scalping."""
        distance = abs(price - vwap) / vwap if vwap != 0 else 0

        if distance > distance_threshold:  # Price moved away from VWAP by more than threshold
            if price > vwap:  # Price above VWAP - potential reversal to downside
                return SignalType.SELL  # Potential short opportunity
            else:  # Price below VWAP - potential reversal to upside
                return SignalType.BUY   # Potential long opportunity
        return None  # No reversal detected

    def _analyze_microstructure(self, high: float, low: float, close: float, volume: float,
                               prev_high: float, prev_low: float, prev_close: float) -> Dict[str, float]:
        """Analyze market microstructure for scalping signals."""
        analysis = {}

        # Calculate spreads and ranges
        current_range = high - low
        prev_range = prev_high - prev_low
        average_range = (current_range + prev_range) / 2

        # Price position within range (for microstructure signals)
        price_position = (close - low) / (current_range if current_range > 0 else 1) if current_range > 0 else 0.5

        # Volume characteristics (relative to recent history)
        analysis['range_expansion'] = current_range / (average_range if average_range > 0 else 1) if average_range > 0 else 1.0
        analysis['price_position'] = price_position
        analysis['bullish_engulfing'] = 1.0 if close > prev_high else 0.0
        analysis['bearish_engulfing'] = 1.0 if close < prev_low else 0.0
        analysis['inverted_hammer'] = 1.0 if price_position < 0.2 and current_range > average_range * 1.5 else 0.0
        analysis['shooting_star'] = 1.0 if price_position > 0.8 and current_range > average_range * 1.5 else 0.0

        return analysis

    def _calculate_high_freq_indicators(self, change_3m: float, change_5m: float, change_15m: float) -> Dict[str, float]:
        """Calculate high-frequency indicators for scalping using realistic timeframes."""
        indicators = {}

        # Momentum divergence across timeframes (using more reliable timeframes)
        indicators['momentum_alignment'] = 1.0 if ((change_3m >= 0) == (change_5m >= 0)) and ((change_5m >= 0) == (change_15m >= 0)) else 0.0

        # Short-term momentum strength
        indicators['short_term_momentum'] = abs(change_3m) + abs(change_5m)

        # Momentum convergence/divergence
        indicators['momentum_convergence'] = abs(change_3m - change_5m) if abs(change_3m - change_5m) < 2.0 else 2.0

        # Trend acceleration (difference in momentum between shorter timeframes)
        indicators['trend_acceleration'] = change_3m - change_5m

        return indicators

    def _detect_liquidity_sweeps(self, high: float, low: float, prev_high: float, prev_low: float,
                                 open_price: float, close: float) -> Optional[str]:
        """Detect liquidity sweeps for scalping opportunities."""
        # Bullish sweep: price went below prev_low and then reversed to close above open
        bullish_sweep = (low < prev_low) and (close > open_price)

        # Bearish sweep: price went above prev_high and then reversed to close below open
        bearish_sweep = (high > prev_high) and (close < open_price)

        if bullish_sweep:
            return 'BULLISH_SWEEP'
        elif bearish_sweep:
            return 'BEARISH_SWEEP'
        else:
            return None

    def _get_timeframe_data(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Fetch data for specific timeframes for scalping analysis."""
        # This would normally fetch data from the broker/exchange for different timeframes
        # Since we're working with CMC which has limited timeframe data,
        # this is a placeholder showing how it would work with actual exchange data
        cache_key = f"timeframe:{symbol}:{timeframe}"
        cached_data = self._get_from_general_cache(cache_key)
        if cached_data:
            return cached_data

        # In a real implementation, this would fetch specific timeframe data from exchange
        # For now, return None to indicate that it's not available through CMC
        return None

    def _analyze_scalping_signals(self, symbol: Symbol, cmc_data: Dict[str, Any]) -> Optional[Signal]:
        """Analyze scalping-specific signals using multiple indicators."""
        from datetime import datetime

        # Extract available data
        price = cmc_data.get('price', 0)
        high = cmc_data.get('high', price * 1.01)  # Use a proxy if not available
        low = cmc_data.get('low', price * 0.99)    # Use a proxy if not available
        close = cmc_data.get('price', price)       # Current price as close
        volume = cmc_data.get('volume_24h', 0)
        change_1h = cmc_data.get('percent_change_1h', 0)
        change_24h = cmc_data.get('percent_change_24h', 0)

        # For true scalping, we need access to more granular data (OHLCV at shorter timeframes)
        # This is typically obtained from exchange APIs directly rather than CMC
        # For demonstration purposes, we'll simulate short-term indicators based on available data

        # Calculate volatility levels for scalping (higher volatility = more scalping opportunities)
        volatility = abs(change_1h) / 100.0

        # Microstructure analysis (simplified)
        microstructure = self._analyze_microstructure(high, low, close, volume,
                                                    high * 0.995, low * 1.005, close * 0.998)  # Simulated previous values

        # Scalping opportunity analysis
        opportunity_score = 0.0
        signal_type = SignalType.NEUTRAL

        # Look for high volatility situations (good for scalping)
        if volatility > 0.03:  # 3% hourly movement
            # Higher probability of reversals and momentum shifts
            opportunity_score += 0.3
            if change_1h > 2.0:  # Strong momentum, might reverse
                signal_type = SignalType.SELL
                opportunity_score += 0.2
            elif change_1h < -2.0:  # Strong downtrend, might bounce
                signal_type = SignalType.BUY
                opportunity_score += 0.2

        # Look for price range positions that indicate potential reversals
        if microstructure['price_position'] > 0.8:  # Near high of range
            signal_type = SignalType.SELL
            opportunity_score += 0.15
        elif microstructure['price_position'] < 0.2:  # Near low of range
            signal_type = SignalType.BUY
            opportunity_score += 0.15

        # Look for engulfing patterns
        if microstructure['bullish_engulfing'] > 0:
            signal_type = SignalType.BUY
            opportunity_score += 0.1
        elif microstructure['bearish_engulfing'] > 0:
            signal_type = SignalType.SELL
            opportunity_score += 0.1

        # Adjust confidence based on opportunity score
        if opportunity_score > 0:
            base_confidence = Decimal('0.5')
            additional_confidence = min(Decimal('0.4'), Decimal(str(opportunity_score)))
            confidence = Percentage(base_confidence + additional_confidence)
            score = max(-1.0, min(1.0, opportunity_score))  # Clamp to [-1.0, 1.0]
        else:
            return None  # No clear scalping opportunity

        # Create and return scalping signal
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=f"{self.name}_Scalping",
            timestamp=datetime.now(),
            source_engine="CMCScreener_Scalping",
            metadata={
                'cmc_data': cmc_data,
                'volatility': volatility,
                'microstructure_analysis': microstructure,
                'scalping_score': opportunity_score,
                'high_frequency_indicators': {},
                'analysis_type': 'scalping_analysis',
                'timeframe_analysis': {
                    '1h_change': change_1h,
                    '24h_change': change_24h
                }
            }
        )

