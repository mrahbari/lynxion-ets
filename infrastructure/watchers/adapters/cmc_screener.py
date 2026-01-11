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

from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from domain.ports.watcher_ports import WatcherPort
from shared.logger import EnhancedLogger
from dotenv import load_dotenv


class CMCScreener(WatcherPort):
    """Optimized CoinMarketCap Screener - provides universe observations, not trade signals."""

    def __init__(self, name: str = "CMCScreener", symbol: str = "BTCUSDT"):
        self.name = name
        self.symbol = Symbol(symbol)
        self._is_running = False
        self.last_observation: Optional[MarketObservation] = None

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

        # Initialize CMC API configuration
        self.cmc_api_key = os.getenv("CMC_API_KEY")
        self.cmc_listings_url = os.getenv("CMC_LISTINGS_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")
        self.cmc_quotes_url = os.getenv("CMC_QUOTES_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest")
        self.cmc_categories_url = os.getenv("CMC_CATEGORIES_URL", "https://pro-api.coinmarketcap.com/data-api/v3/cryptocurrency/categorization")

        # Initialize data structures
        self.market_data = {}
        self.price_history = defaultdict(deque)
        self.volume_history = defaultdict(deque)
        self.market_cap_history = defaultdict(deque)
        self.last_update_time = time.time()
        self.update_interval = int(os.getenv("CMC_UPDATE_INTERVAL", "300"))  # 5 minutes default
        self.data_lock = Lock()

        # Initialize performance tracking
        self.performance_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'last_error_time': None,
            'error_rate': 0.0
        }

        # Initialize market condition tracking
        self.market_conditions = {
            'volatility_regime': 'normal',
            'trend_regime': 'sideways',
            'momentum_regime': 'neutral',
            'liquidity_regime': 'normal'
        }

        # Initialize thresholds for different market conditions
        self.volatility_threshold_high = float(os.getenv("CMC_VOLATILITY_HIGH_THRESHOLD", "0.05"))  # 5%
        self.volatility_threshold_low = float(os.getenv("CMC_VOLATILITY_LOW_THRESHOLD", "0.01"))  # 1%
        self.volume_threshold_high = float(os.getenv("CMC_VOLUME_HIGH_THRESHOLD", "2.0"))  # 2x average
        self.volume_threshold_low = float(os.getenv("CMC_VOLUME_LOW_THRESHOLD", "0.5"))  # 0.5x average

    def analyze(self, symbol: Symbol) -> Optional[MarketObservation]:
        """Analyze market conditions and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        try:
            # Fetch latest market data if needed
            if time.time() - self.last_update_time > self.update_interval:
                self._fetch_market_data()
                self.last_update_time = time.time()

            # Analyze market conditions
            market_observation = self._analyze_market_conditions(symbol)

            # Update last observation if it's different enough and not None
            if market_observation and self._should_emit_observation(market_observation):
                self.last_observation = market_observation
                self.logger.debug(f"CMCScreener generated observation: {market_observation.observation_type} for {symbol.value}")

            return market_observation

        except Exception as e:
            self.logger.error(f"Error in CMCScreener analysis: {e}")
            return None

    def _analyze_market_conditions(self, symbol: Symbol) -> Optional[MarketObservation]:
        """Analyze current market conditions and return a market observation"""
        if not self.market_data:
            return None

        # Determine which coin data to analyze
        target_symbol = symbol.value
        if target_symbol not in self.market_data:
            # If specific symbol not found, analyze overall market
            target_symbol = next(iter(self.market_data.keys()), None)
            if not target_symbol:
                return None

        coin_data = self.market_data.get(target_symbol)
        if not coin_data:
            return None

        # Extract relevant data
        price = coin_data.get('price', 0)
        volume_24h = coin_data.get('volume_24h', 0)
        market_cap = coin_data.get('market_cap', 0)
        percent_change_24h = coin_data.get('percent_change_24h', 0)
        percent_change_7d = coin_data.get('percent_change_7d', 0)

        # Calculate volatility based on historical data
        volatility = self._calculate_volatility(target_symbol)
        
        # Calculate volume relative to historical average
        avg_volume = self._calculate_average_volume(target_symbol)
        volume_ratio = volume_24h / avg_volume if avg_volume > 0 else 1.0

        # Determine market condition observation type
        observation_type = self._determine_observation_type(
            volatility, volume_ratio, percent_change_24h, percent_change_7d
        )

        # Calculate observation value based on market conditions
        observation_value = self._calculate_observation_value(
            volatility, volume_ratio, percent_change_24h, percent_change_7d
        )

        # Calculate confidence based on data quality and market conditions
        confidence = self._calculate_confidence(volatility, volume_ratio, percent_change_24h)

        # Create and return MarketObservation
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=observation_value,
            confidence=Percentage(Decimal(str(confidence))),
            timestamp=datetime.now(),
            metadata={
                'cmc_data': {
                    'price': price,
                    'volume_24h': volume_24h,
                    'market_cap': market_cap,
                    'percent_change_24h': percent_change_24h,
                    'percent_change_7d': percent_change_7d
                },
                'calculated_metrics': {
                    'volatility': volatility,
                    'volume_ratio': volume_ratio,
                    'avg_volume': avg_volume
                },
                'market_conditions': {
                    'volatility_regime': self._get_volatility_regime(volatility),
                    'volume_regime': self._get_volume_regime(volume_ratio),
                    'momentum_regime': self._get_momentum_regime(percent_change_24h)
                },
                'cmc_source': self.name,
                'data_timestamp': coin_data.get('last_updated', datetime.now().isoformat())
            }
        )

        return observation

    def _determine_observation_type(self, volatility: float, volume_ratio: float, 
                                   change_24h: float, change_7d: float) -> str:
        """Determine the type of market observation based on conditions"""
        if volatility > self.volatility_threshold_high:
            return 'cmc_high_volatility'
        elif volatility < self.volatility_threshold_low:
            return 'cmc_low_volatility'
        elif volume_ratio > self.volume_threshold_high:
            return 'cmc_high_volume'
        elif volume_ratio < self.volume_threshold_low:
            return 'cmc_low_volume'
        elif change_24h > 5.0:  # 5% gain in 24h
            return 'cmc_momentum_positive'
        elif change_24h < -5.0:  # 5% loss in 24h
            return 'cmc_momentum_negative'
        else:
            return 'cmc_market_normal'

    def _calculate_observation_value(self, volatility: float, volume_ratio: float, 
                                   change_24h: float, change_7d: float) -> float:
        """Calculate a numerical observation value based on market conditions"""
        # Normalize and combine different factors
        vol_factor = min(1.0, volatility * 10)  # Scale volatility appropriately
        vol_ratio_factor = min(1.0, max(-1.0, volume_ratio - 1.0))  # Center around 1.0
        change_factor = min(1.0, max(-1.0, change_24h / 10.0))  # Scale 10% changes to 1.0
        
        # Combine factors with weights
        combined_value = (vol_factor * 0.3 + vol_ratio_factor * 0.3 + change_factor * 0.4)
        
        return max(-1.0, min(1.0, combined_value))

    def _calculate_confidence(self, volatility: float, volume_ratio: float, change_24h: float) -> float:
        """Calculate confidence based on market conditions"""
        # Higher volatility and volume generally mean more reliable signals
        vol_confidence = min(1.0, volatility * 5)  # Higher volatility = higher confidence up to a point
        volume_confidence = min(1.0, max(0.1, volume_ratio * 0.5))  # Higher volume = higher confidence
        change_confidence = min(1.0, abs(change_24h) / 10.0)  # Larger changes = higher confidence
        
        # Combine with configurable weights
        import os
        vol_weight = float(os.getenv('CMC_VOL_CONFIDENCE_WEIGHT', '0.3'))
        volume_weight = float(os.getenv('CMC_VOLUME_CONFIDENCE_WEIGHT', '0.4'))
        change_weight = float(os.getenv('CMC_CHANGE_CONFIDENCE_WEIGHT', '0.3'))

        confidence = (vol_confidence * vol_weight + volume_confidence * volume_weight + change_confidence * change_weight)

        min_cmc_confidence = float(os.getenv('CMC_MIN_CONFIDENCE_THRESHOLD', '0.1'))
        return max(min_cmc_confidence, min(1.0, confidence))  # Ensure minimum confidence based on config

    def _calculate_volatility(self, symbol: str) -> float:
        """Calculate volatility for a specific symbol based on historical prices"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return 0.0

        prices = list(self.price_history[symbol])
        if len(prices) < 2:
            return 0.0

        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])

        if not returns:
            return 0.0

        # Calculate standard deviation of returns
        import numpy as np
        return float(np.std(returns))

    def _calculate_average_volume(self, symbol: str) -> float:
        """Calculate average volume for a specific symbol"""
        if symbol not in self.volume_history or not self.volume_history[symbol]:
            return 0.0

        volumes = list(self.volume_history[symbol])
        import numpy as np
        return float(np.mean(volumes)) if volumes else 0.0

    def _get_volatility_regime(self, volatility: float) -> str:
        """Get volatility regime based on threshold"""
        if volatility > self.volatility_threshold_high:
            return 'high'
        elif volatility < self.volatility_threshold_low:
            return 'low'
        else:
            return 'normal'

    def _get_volume_regime(self, volume_ratio: float) -> str:
        """Get volume regime based on ratio"""
        if volume_ratio > self.volume_threshold_high:
            return 'high'
        elif volume_ratio < self.volume_threshold_low:
            return 'low'
        else:
            return 'normal'

    def _get_momentum_regime(self, change_24h: float) -> str:
        """Get momentum regime based on 24h change"""
        if change_24h > 5.0:
            return 'high_positive'
        elif change_24h < -5.0:
            return 'high_negative'
        elif change_24h > 1.0:
            return 'positive'
        elif change_24h < -1.0:
            return 'negative'
        else:
            return 'neutral'

    def _should_emit_observation(self, current_observation: Optional[MarketObservation]) -> bool:
        """Determine if a new observation should be emitted"""
        if not current_observation or not self.last_observation:
            return True

        # Don't emit if the same observation type was generated recently with similar confidence
        return (current_observation.observation_type != self.last_observation.observation_type or
                abs(float(current_observation.confidence.value) - float(self.last_observation.confidence.value)) > 0.1)

    def _fetch_market_data(self):
        """Fetch market data from CMC API"""
        if not self.cmc_api_key:
            self.logger.warning("CMC API key not found, skipping data fetch")
            return

        headers = {
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
            'Accept': 'application/json'
        }

        try:
            # Fetch top cryptocurrencies
            params = {
                'start': '1',
                'limit': '100',  # Get top 100 coins
                'convert': 'USD'
            }

            response = requests.get(self.cmc_listings_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if 'data' in data:
                with self.data_lock:
                    for coin in data['data']:
                        symbol = coin['symbol']
                        quote = coin['quote']['USD'] if 'quote' in coin and 'USD' in coin['quote'] else {}
                        
                        # Store relevant data
                        self.market_data[symbol] = {
                            'price': quote.get('price', 0),
                            'volume_24h': quote.get('volume_24h', 0),
                            'market_cap': quote.get('market_cap', 0),
                            'percent_change_24h': quote.get('percent_change_24h', 0),
                            'percent_change_7d': quote.get('percent_change_7d', 0),
                            'last_updated': datetime.now().isoformat()
                        }

                        # Update historical data
                        if quote.get('price'):
                            self.price_history[symbol].append(quote['price'])
                            if len(self.price_history[symbol]) > 100:  # Keep last 100 prices
                                self.price_history[symbol].popleft()

                        if quote.get('volume_24h'):
                            self.volume_history[symbol].append(quote['volume_24h'])
                            if len(self.volume_history[symbol]) > 100:  # Keep last 100 volumes
                                self.volume_history[symbol].popleft()

                        if quote.get('market_cap'):
                            self.market_cap_history[symbol].append(quote['market_cap'])
                            if len(self.market_cap_history[symbol]) > 100:  # Keep last 100 market caps
                                self.market_cap_history[symbol].popleft()

                self.performance_metrics['successful_requests'] += 1
            else:
                self.logger.warning("No data received from CMC API")

        except Exception as e:
            self.logger.error(f"Error fetching CMC data: {e}")
            self.performance_metrics['failed_requests'] += 1
            self.performance_metrics['last_error_time'] = datetime.now()

        finally:
            self.performance_metrics['total_requests'] += 1
            self.performance_metrics['error_rate'] = (
                self.performance_metrics['failed_requests'] / 
                max(1, self.performance_metrics['total_requests'])
            )

    def start(self):
        """Start the watcher"""
        self._is_running = True
        self.logger.info(f"CMCScreener started for symbol: {self.symbol.value}")

    def stop(self):
        """Stop the watcher"""
        self._is_running = False
        self.logger.info(f"CMCScreener stopped for symbol: {self.symbol.value}")

    def is_running(self) -> bool:
        """Check if the watcher is currently running"""
        return self._is_running

    def update_data(self, data: Dict[str, Any]):
        """Update the watcher with new market data"""
        # CMC screener fetches its own data, so this is a no-op
        pass