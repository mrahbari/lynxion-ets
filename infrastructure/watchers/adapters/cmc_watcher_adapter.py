"""
CMC Watcher Adapter implementing the WatcherPort interface for CoinMarketCap based market analysis.
"""
import threading
import time
from typing import Dict, List, Optional, Any
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.watcher_ports import WatcherPort
from shared.logger import EnhancedLogger
from decimal import Decimal
import os
import requests
from dotenv import load_dotenv


class CMCWatcherAdapter(WatcherPort):
    """CMC Watcher adapter that implements WatcherPort interface for CoinMarketCap based market analysis."""

    def __init__(self, symbol: Symbol):
        self.symbol = symbol
        self.name = "CMCWatcher"
        self._is_running = False
        self.last_signal: Optional[Signal] = None
        self.logger = EnhancedLogger(f"CMCWatcherAdapter_{symbol.value}")
        self.update_interval = 300  # Update every 5 minutes

        # Load CMC API configuration from environment
        load_dotenv()
        self.cmc_api_key = os.getenv("CMC_API_KEY")
        if not self.cmc_api_key:
            self.logger.warning("CMC_API_KEY not found in environment variables. CMCWatcher will not function without it.")
        
        self.cmc_api_url = os.getenv("CMC_QUOTES_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest")
        self.cmc_listings_url = os.getenv("CMC_LISTINGS_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market conditions using CMC data and return a signal."""
        if not self.cmc_api_key:
            self.logger.warning("CMC_API_KEY not configured, cannot analyze market")
            return None

        try:
            # Fetch data from CMC
            self.logger.log_watcher_analysis(self.name, symbol.value, "Fetching data from CoinMarketCap")
            cmc_data = self._fetch_cmc_data(symbol)
            if not cmc_data:
                self.logger.warning(f"Could not fetch CMC data for {symbol.value}")
                return None

            # Perform analysis based on CMC data
            self.logger.log_watcher_analysis(self.name, symbol.value, "Analyzing CMC market data")
            signal = self._analyze_cmc_data(symbol, cmc_data)

            if signal and self._should_emit_signal(signal):
                self.last_signal = signal
                confidence_val = float(signal.confidence.value)
                self.logger.log_watcher_analysis(self.name, symbol.value, f"Generated {signal.signal_type.name} signal with {confidence_val:.2%} confidence", confidence=confidence_val, signal_type=signal.signal_type.name)
                return signal
            else:
                self.logger.log_watcher_analysis(self.name, symbol.value, "Signal filtered due to similarity with last signal")
                return signal  # Return even if not emitted for consistency

        except Exception as e:
            self.logger.error(f"Error in CMC analysis for {symbol.value}: {e}")
            return None

    def _fetch_cmc_data(self, symbol: Symbol) -> Optional[Dict[str, Any]]:
        """Fetch cryptocurrency data from CoinMarketCap API."""
        # Extract the base cryptocurrency symbol from various formats
        # e.g., BTCUSDT -> BTC, BTC -> BTC
        base_symbol = self._extract_base_symbol(symbol.value)
        
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
                # Get the first (and should be only) cryptocurrency in the result
                crypto_data = list(data['data'].values())[0] if isinstance(data['data'], dict) else data['data'][0] if isinstance(data['data'], list) else None

                if crypto_data:
                    quote = crypto_data.get('quote', {}).get('USD', {})

                    return {
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
                    }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching CMC data for {symbol.value}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing CMC data for {symbol.value}: {e}")

        return None

    def _extract_base_symbol(self, symbol: str) -> str:
        """Extract the base cryptocurrency symbol from various formats."""
        # Handle symbols like BTCUSDT, etc.
        if len(symbol) > 3 and symbol.endswith(('USDT', 'USD', 'BTC', 'ETH', 'BNB')):
            # For BTCUSDT, BTCUSD, etc., return base part
            quote_parts = ['USDT', 'USD', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP', 'USDC']
            for part in quote_parts:
                if symbol.endswith(part):
                    return symbol[:-len(part)]
            # If no known quote asset found, return first 3-6 chars
            return symbol[:3] if len(symbol) > 6 else symbol[:6]
        else:
            # For simple symbols like BTC, return as is (max 5 chars to be safe)
            return symbol[:5]

    def _analyze_cmc_data(self, symbol: Symbol, cmc_data: Dict[str, Any]) -> Optional[Signal]:
        """Analyze CMC data to generate a trading signal."""
        from datetime import datetime
        
        # Check if the coin is a stablecoin (should be excluded)
        if self._is_stablecoin(cmc_data):
            return None

        # Analyze the CMC data to determine signal
        percent_change_24h = cmc_data.get('percent_change_24h', 0)
        percent_change_1h = cmc_data.get('percent_change_1h', 0)
        volume_24h = cmc_data.get('volume_24h', 0)
        market_cap = cmc_data.get('market_cap', 0)

        # Determine signal type based on CMC data
        if percent_change_24h > 10:  # Strong upward momentum
            signal_type = SignalType.BUY
            confidence = Percentage(Decimal('0.85'))
            score = min(1.0, percent_change_24h / 100.0)  # Convert percentage to score
        elif percent_change_24h < -10:  # Strong downward momentum
            signal_type = SignalType.SELL
            confidence = Percentage(Decimal('0.85'))
            score = max(-1.0, percent_change_24h / 100.0)  # Convert percentage to negative score
        elif percent_change_1h > 5 and volume_24h > 1000000:  # Short-term momentum with volume
            signal_type = SignalType.BUY
            confidence = Percentage(Decimal('0.7'))
            score = min(0.8, percent_change_1h / 100.0)
        elif percent_change_1h < -5 and volume_24h > 1000000:  # Short-term decline with volume
            signal_type = SignalType.SELL
            confidence = Percentage(Decimal('0.7'))
            score = max(-0.8, percent_change_1h / 100.0)
        elif abs(percent_change_24h) < 3:  # Low volatility, likely sideways action
            signal_type = SignalType.HOLD
            confidence = Percentage(Decimal('0.4'))
            score = 0.0
        else:  # Neutral market
            signal_type = SignalType.NEUTRAL
            confidence = Percentage(Decimal('0.5'))
            score = percent_change_24h / 200.0  # Normalize to -1 to 1 range

        # Create and return signal
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="CMCWatcher",
            metadata={
                'cmc_data': cmc_data,
                'percent_change_24h': percent_change_24h,
                'percent_change_1h': percent_change_1h,
                'volume_24h': volume_24h,
                'market_cap': market_cap,
                'analysis_type': 'cmc_market_sentiment'
            }
        )

        return signal

    def _is_stablecoin(self, coin_data: Dict[str, Any]) -> bool:
        """Check if a coin is a stablecoin using multiple criteria."""
        symbol = coin_data.get('symbol', '')
        price = coin_data.get('price', 0)
        tags = coin_data.get('tags', [])

        # Known stablecoin symbols
        stablecoin_symbols = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FRAX', 'PYUSD', 'GUSD', 'USDD', 'EURT']
        
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

    def _should_emit_signal(self, current_signal: Signal) -> bool:
        """Determine if a new signal should be emitted."""
        if not self.last_signal:
            return True

        # Don't emit if the same signal type was generated recently with similar confidence
        same_signal_type = current_signal.signal_type == self.last_signal.signal_type
        confidence_diff = abs(float(current_signal.confidence.value) - float(self.last_signal.confidence.value))
        
        return not (same_signal_type and confidence_diff < 0.1)

    def start(self):
        """Start the CMC watcher."""
        self._is_running = True
        self.logger.log_watcher_analysis("CMCWatcher", self.symbol.value, "Started", 1.0)

    def stop(self):
        """Stop the CMC watcher."""
        self._is_running = False
        self.logger.log_watcher_analysis("CMCWatcher", self.symbol.value, "Stopped", 1.0)

    def update_data(self, data: Dict[str, Any]):
        """Update the watcher with new market data."""
        # CMC watcher primarily fetches data from external API
        # This method is kept for interface compatibility
        pass

    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._is_running


class CMCScreenerAdapter(WatcherPort):
    """CMC Screener adapter that screens multiple coins and identifies opportunities."""

    def __init__(self, name: str = "CMCScreener"):
        self.name = name
        self.symbol = Symbol("USDTUSDT")  # Use a dummy symbol to comply with validation
        self._is_running = False
        self.last_signal: Optional[Signal] = None
        self.logger = EnhancedLogger(f"CMCScreenerAdapter")
        
        # Load CMC API configuration from environment
        load_dotenv()
        self.cmc_api_key = os.getenv("CMC_API_KEY")
        if not self.cmc_api_key:
            self.logger.warning("CMC_API_KEY not found in environment variables. CMCScreener will not function "
                                "without it.")
        
        self.cmc_api_url = os.getenv("CMC_QUOTES_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest")
        self.cmc_listings_url = os.getenv("CMC_LISTINGS_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")
        
        # Excluded coins configuration
        excluded_coins_str = os.getenv("CMC_EXCLUDED_COINS", "BTC,ETH,SOL,ADA,DOT,XRP,DOGE,LINK,BNB,AVAX,MATIC")
        self.excluded_coins = set(coin.strip().upper() for coin in excluded_coins_str.split(',') if coin.strip())

    def analyze(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze market conditions and return a signal based on CMC screening."""
        if not self.cmc_api_key:
            self.logger.warning("CMC_API_KEY not configured, cannot perform screening")
            return None

        try:
            # If the special "USDTUSDT" symbol is provided, screen top coins for general market sentiment
            # This is our way of indicating "analyze the overall market"
            if symbol.value == "USDTUSDT":
                self.logger.log_watcher_analysis("CMCScreener", "MARKET", "Screening top coins for market sentiment")
                result = self._screen_top_coins()
                return result

            # Otherwise analyze the specific symbol
            self.logger.log_watcher_analysis("CMCScreener", symbol.value, "Analyzing specific symbol")
            result = self._analyze_specific_symbol(symbol)
            return result

        except Exception as e:
            self.logger.error(f"Error in CMC screening: {e}")
            return None

    def _analyze_specific_symbol(self, symbol: Symbol) -> Optional[Signal]:
        """Analyze a specific symbol using CMC data."""
        # Extract base symbol
        base_symbol = self._extract_base_symbol(symbol.value)
        
        # Skip excluded coins
        if base_symbol in self.excluded_coins:
            return None

        cmc_data = self._fetch_cmc_data(base_symbol)
        if not cmc_data:
            return None

        return self._analyze_cmc_data(symbol, cmc_data)

    def _screen_top_coins(self) -> Optional[Signal]:
        """Screen top coins to determine overall market sentiment."""
        from datetime import datetime

        self.logger.log_watcher_analysis("CMCScreener", "MARKET", "Fetching top 50 coins for screening")
        top_coins = self._fetch_top_cryptocurrencies(limit=50)
        if not top_coins:
            self.logger.warning("Could not fetch top cryptocurrencies for screening")
            return None

        growth_count = 0
        crash_count = 0
        total_analyzed = 0

        self.logger.log_watcher_analysis("CMCScreener", "MARKET", f"Screening {len(top_coins)} top coins", total_coins=len(top_coins))
        for coin in top_coins:
            coin_symbol = coin.get('symbol', '').upper()

            # Skip excluded coins
            if coin_symbol in self.excluded_coins:
                continue

            # Skip if it's a stablecoin
            if self._is_stablecoin(coin):
                continue

            # Get coin data
            coin_data = {
                'symbol': coin_symbol,
                'name': coin.get('name', ''),
                'rank': coin.get('cmc_rank', 0),
                'price': coin.get('quote', {}).get('USD', {}).get('price', 0),
                'market_cap': coin.get('quote', {}).get('USD', {}).get('market_cap', 0),
                'volume_24h': coin.get('quote', {}).get('USD', {}).get('volume_24h', 0),
                'percent_change_1h': coin.get('quote', {}).get('USD', {}).get('percent_change_1h', 0),
                'percent_change_24h': coin.get('quote', {}).get('USD', {}).get('percent_change_24h', 0),
                'tags': coin.get('tags', []),
            }

            # Determine if this coin shows growth potential or crash risk
            is_growth, _ = self._check_growth_potential(coin_data)
            is_crash, _ = self._check_crash_risk(coin_data)

            if is_growth:
                growth_count += 1
            elif is_crash:
                crash_count += 1

            total_analyzed += 1

        # Determine overall market signal based on the ratio of growth vs crash coins
        if total_analyzed == 0:
            self.logger.info("No coins analyzed - all were excluded or filtered out")
            return None

        growth_ratio = growth_count / total_analyzed
        crash_ratio = crash_count / total_analyzed

        self.logger.log_watcher_analysis("CMCScreener", "MARKET", f"Screening results: {total_analyzed} coins analyzed, {growth_count} growth, {crash_count} crash-risk", total_analyzed=total_analyzed, growth_count=growth_count, crash_count=crash_count)

        if growth_ratio > 0.3:  # More than 30% show growth potential
            signal_type = SignalType.BUY
            confidence = min(Decimal('0.9'), Decimal('0.4') + Decimal(str(growth_ratio)))
            score = min(0.8, growth_ratio * 2)
        elif crash_ratio > 0.2:  # More than 20% show crash risk
            signal_type = SignalType.SELL
            confidence = min(Decimal('0.9'), Decimal('0.4') + Decimal(str(crash_ratio)))
            score = max(-0.8, -crash_ratio * 3)
        else:
            signal_type = SignalType.HOLD
            confidence = Decimal('0.5')
            score = 0.0

        signal = Signal(
            symbol=Symbol("MARKET"),
            signal_type=signal_type,
            confidence=Percentage(confidence),
            score=score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="CMCScreener",
            metadata={
                'total_analyzed': total_analyzed,
                'growth_count': growth_count,
                'crash_count': crash_count,
                'growth_ratio': growth_ratio,
                'crash_ratio': crash_ratio,
                'screening_type': 'market_sentiment'
            }
        )

        if self._should_emit_signal(signal):
            self.last_signal = signal
            confidence_val = float(confidence)
            self.logger.log_watcher_analysis("CMCScreener", "MARKET", f"Generated {signal_type.name} market signal with {confidence_val:.2%} confidence (growth: {growth_ratio:.2%}, crash: {crash_ratio:.2%})", confidence=confidence_val, signal_type=signal_type.name, growth_ratio=growth_ratio, crash_ratio=crash_ratio)
            return signal

        self.logger.log_watcher_analysis("CMCScreener", "MARKET", f"Market signal filtered due to similarity with previous signal (growth: {growth_ratio:.2%}, crash: {crash_ratio:.2%})", growth_ratio=growth_ratio, crash_ratio=crash_ratio)
        return signal

    def _fetch_top_cryptocurrencies(self, limit: int = 100) -> Optional[List[Dict]]:
        """Fetch top cryptocurrencies from CMC listings API."""
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
                return data['data']
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching CMC listings: {e}")
        except Exception as e:
            self.logger.error(f"Error processing CMC listings: {e}")

        return None

    def _fetch_cmc_data(self, symbol: str) -> Optional[Dict]:
        """Fetch cryptocurrency data from CoinMarketCap API."""
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
        }

        params = {'symbol': symbol}

        try:
            response = requests.get(self.cmc_api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                # Get the first cryptocurrency in the result
                crypto_data = list(data['data'].values())[0] if isinstance(data['data'], dict) else data['data'][0]
                if crypto_data:
                    quote = crypto_data.get('quote', {}).get('USD', {})

                    return {
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
                    }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching CMC data for {symbol}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing CMC data for {symbol}: {e}")

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

    def _check_growth_potential(self, coin_data: Dict) -> tuple[bool, List[str]]:
        """Check if a coin qualifies as high-growth potential."""
        reasons = []
        is_growth = True

        # Check 24h change > 8%
        change_24h = coin_data.get('percent_change_24h', 0)
        min_change = 8.0
        if change_24h > min_change:
            reasons.append(f"24h change {change_24h:.2f}% > {min_change}%")
        else:
            is_growth = False
            reasons.append(f"24h change {change_24h:.2f}% <= {min_change}%")

        # Check volume
        volume_24h = coin_data.get('volume_24h', 0)
        min_volume = 2_000_000
        if volume_24h > min_volume:
            reasons.append(f"Volume {volume_24h:,.0f} > {min_volume:,}")
        else:
            is_growth = False
            reasons.append(f"Volume {volume_24h:,.0f} <= {min_volume:,}")

        # Check market cap range
        market_cap = coin_data.get('market_cap', 0)
        max_market_cap = 500_000_000
        min_market_cap = 5_000_000
        if market_cap <= max_market_cap and market_cap > min_market_cap:
            reasons.append(f"Market cap {market_cap:,.0f} in range ({min_market_cap:,}, {max_market_cap:,}]")
        else:
            is_growth = False
            reasons.append(f"Market cap {market_cap:,.0f} outside range ({min_market_cap:,}, {max_market_cap:,}]")

        return is_growth, reasons

    def _check_crash_risk(self, coin_data: Dict) -> tuple[bool, List[str]]:
        """Check if a coin qualifies as high-crash risk."""
        reasons = []
        is_crash_risk = True

        # Check 24h change < -8%
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

    def _is_stablecoin(self, coin_data: Dict) -> bool:
        """Check if a coin is a stablecoin using multiple criteria."""
        symbol = coin_data.get('symbol', '')
        price = coin_data.get('price', 0)
        tags = coin_data.get('tags', [])

        # Known stablecoin symbols
        stablecoin_symbols = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FRAX', 'PYUSD', 'GUSD', 'USDD', 'EURT']
        stablecoin_tags = ['stablecoin', 'asset-backed-stablecoin', 'algorithmic-stablecoin']
        
        # Tag-based filter
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

    def _analyze_cmc_data(self, symbol: Symbol, cmc_data: Dict[str, Any]) -> Optional[Signal]:
        """Analyze CMC data to generate a trading signal."""
        from datetime import datetime
        
        # Check if the coin is a stablecoin (should be excluded)
        if self._is_stablecoin(cmc_data):
            return None

        # Analyze the CMC data to determine signal
        percent_change_24h = cmc_data.get('percent_change_24h', 0)
        percent_change_1h = cmc_data.get('percent_change_1h', 0)
        volume_24h = cmc_data.get('volume_24h', 0)
        market_cap = cmc_data.get('market_cap', 0)

        # Determine signal type based on CMC data
        if percent_change_24h > 10:  # Strong upward momentum
            signal_type = SignalType.BUY
            confidence = Percentage(Decimal('0.85'))
            score = min(1.0, percent_change_24h / 100.0)  # Convert percentage to score
        elif percent_change_24h < -10:  # Strong downward momentum
            signal_type = SignalType.SELL
            confidence = Percentage(Decimal('0.85'))
            score = max(-1.0, percent_change_24h / 100.0)  # Convert percentage to negative score
        elif percent_change_1h > 5 and volume_24h > 1000000:  # Short-term momentum with volume
            signal_type = SignalType.BUY
            confidence = Percentage(Decimal('0.7'))
            score = min(0.8, percent_change_1h / 100.0)
        elif percent_change_1h < -5 and volume_24h > 1000000:  # Short-term decline with volume
            signal_type = SignalType.SELL
            confidence = Percentage(Decimal('0.7'))
            score = max(-0.8, percent_change_1h / 100.0)
        elif abs(percent_change_24h) < 3:  # Low volatility, likely sideways action
            signal_type = SignalType.HOLD
            confidence = Percentage(Decimal('0.4'))
            score = 0.0
        else:  # Neutral market
            signal_type = SignalType.NEUTRAL
            confidence = Percentage(Decimal('0.5'))
            score = percent_change_24h / 200.0  # Normalize to -1 to 1 range

        # Create and return signal
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy_name=self.name,
            timestamp=datetime.now(),
            source_engine="CMCScreener",
            metadata={
                'cmc_data': cmc_data,
                'percent_change_24h': percent_change_24h,
                'percent_change_1h': percent_change_1h,
                'volume_24h': volume_24h,
                'market_cap': market_cap,
                'analysis_type': 'cmc_detailed_analysis'
            }
        )

        return signal

    def _should_emit_signal(self, current_signal: Signal) -> bool:
        """Determine if a new signal should be emitted."""
        if not self.last_signal:
            return True

        # Don't emit if the same signal type was generated recently with similar confidence
        same_signal_type = current_signal.signal_type == self.last_signal.signal_type
        confidence_diff = abs(float(current_signal.confidence.value) - float(self.last_signal.confidence.value))
        
        return not (same_signal_type and confidence_diff < 0.1)

    def start(self):
        """Start the CMC Screener."""
        self._is_running = True
        self.logger.log_watcher_analysis("CMCScreener", "MARKET", "Started market screening", 1.0)

    def stop(self):
        """Stop the CMC Screener."""
        self._is_running = False
        self.logger.log_watcher_analysis("CMCScreener", "MARKET", "Stopped market screening", 1.0)

    def update_data(self, data: Dict[str, Any]):
        """Update the screener with new market data."""
        # CMC screener primarily fetches data from external API
        # This method is kept for interface compatibility
        pass

    def is_running(self) -> bool:
        """Check if the screener is currently running."""
        return self._is_running