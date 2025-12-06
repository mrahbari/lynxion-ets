import os
import requests
from dotenv import load_dotenv
from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional, Tuple
from domain.value_objects import Symbol


class CMCScreenerWatcher(BaseWatcher):
    """Enhanced CoinMarketCap Screener Watcher - identifies high-growth and high-crash risk coins with stablecoin exclusion"""

    def __init__(self, name: str, symbol: str = "ALL", lookback: int = 10):
        super().__init__(name, symbol)
        self.lookback = lookback

        # Load CMC API configuration from environment
        load_dotenv()
        self.cmc_api_key = os.getenv("CMC_API_KEY")
        if not self.cmc_api_key:
            raise ValueError("CMC_API_KEY not found in environment variables")

        # Load CMC API URLs from environment (fallback to defaults if not set)
        self.cmc_api_url = os.getenv("CMC_QUOTES_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest")
        self.cmc_listings_url = os.getenv("CMC_LISTINGS_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

        # Load excluded coins from environment (comma-separated list)
        excluded_coins_str = os.getenv("CMC_EXCLUDED_COINS", "BTC,ETH,SOL,ADA,DOT,XRP,DOGE,LINK,BNB,AVAX,MATIC")
        self.excluded_coins = set(coin.strip().upper() for coin in excluded_coins_str.split(',') if coin.strip())

        # For comprehensive screening, we store data about multiple coins
        self.coins_data: Dict[str, Dict] = {}
        self.screening_results: Dict[str, Dict] = {}

        # Thresholds for various filters
        self.stablecoin_tags = ['stablecoin', 'asset-backed-stablecoin', 'algorithmic-stablecoin']
        self.stablecoin_symbols = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FRAX', 'PYUSD', 'GUSD', 'USDD', 'EURT', 'UST', 'FEI', 'TRIBE']

        # Growth potential filters (adjusted to avoid overfitting)
        self.growth_filters = {
            'min_24h_change': 8.0,   # Reduced from 15% to 8% to detect smaller moves
            'min_volume_24h': 2_000_000,  # Reduced from 5M to 2M to include more coins
            'max_market_cap': 500_000_000,  # Reduced from 1B to 500M to focus on smaller caps
            'min_market_cap': 5_000_000,  # Reduced from 10M to 5M to include emerging coins
            'min_volatility': 0.04,  # Reduced from 6% to 4% to detect more movements
            'min_liquidity_ratio': 0.04,  # Reduced from 8% to 4% for more inclusiveness
            'use_ma_filters': True
        }

        # Crash risk filters (adjusted to avoid overfitting)
        self.crash_filters = {
            'max_24h_change': -8.0,   # Reduced from -15% to -8% to detect smaller drops
            'min_volume_24h': 1_000_000,  # Reduced from 2M to 1M for more inclusiveness
            'min_volume_change': 15.0,  # Reduced from 20% to 15%
            'high_volatility_threshold': 0.05,  # Reduced from 7% to 5%
            'use_ma_filters': True
        }

    def fetch_all_cryptocurrencies(self, limit: int = 100) -> Optional[List[Dict]]:
        """Fetch top cryptocurrencies from CMC listings API"""
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
            logger.error(f"Error fetching CMC listings: {e}")
        except Exception as e:
            logger.error(f"Error processing CMC listings: {e}")

        return None

    def fetch_cmc_data(self, symbol: str = None) -> Optional[Dict]:
        """Fetch cryptocurrency data from CoinMarketCap API"""
        if not symbol:
            symbol = self.symbol

        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.cmc_api_key,
        }

        # Extract the base cryptocurrency symbol from various formats
        # e.g., BTC-USDT -> BTC, BTCUSDT -> BTC, BTC -> BTC
        base_symbol = self.extract_base_symbol(symbol)
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

                    # Additional data fields for enhanced analysis
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
                    }

                    # Add price data for volatility calculation if available
                    if 'circulating_supply' in crypto_data and crypto_data['circulating_supply']:
                        result['circulating_supply'] = crypto_data['circulating_supply']

                    return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching CMC data for {symbol} (base: {base_symbol}): {e}")
        except Exception as e:
            logger.error(f"Error processing CMC data for {symbol} (base: {base_symbol}): {e}")

        return None

    def extract_base_symbol(self, symbol: str) -> str:
        """Extract the base cryptocurrency symbol from various formats"""
        # Handle symbols like BTC-USDT, BTCUSDT, etc.
        if '-' in symbol:
            # For BTC-USDT, return BTC
            return symbol.split('-')[0]
        elif len(symbol) > 3 and symbol.endswith(('USDT', 'USD', 'BTC', 'ETH', 'BNB')):
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

    def update_data(self, data: Dict):
        """Update with new market data (backward compatibility)"""
        # For backward compatibility with single-coin analysis
        if 'market_cap' in data:
            symbol = data.get('symbol', 'UNKNOWN')
            if symbol not in self.coins_data:
                self.coins_data[symbol] = {
                    'market_cap_history': [],
                    'volume_history': [],
                    'rank_history': [],
                    'price_history': []
                }

            # Update market cap history
            market_cap = float(data['market_cap'])
            self.coins_data[symbol]['market_cap_history'].append(market_cap)
            if len(self.coins_data[symbol]['market_cap_history']) > self.lookback * 2:
                self.coins_data[symbol]['market_cap_history'].pop(0)

            # Update rank history
            if 'rank' in data:
                rank = int(data['rank'])
                self.coins_data[symbol]['rank_history'].append(rank)
                if len(self.coins_data[symbol]['rank_history']) > self.lookback * 2:
                    self.coins_data[symbol]['rank_history'].pop(0)

            # Update price history
            if 'price' in data:
                price = float(data['price'])
                self.coins_data[symbol]['price_history'].append(price)
                if len(self.coins_data[symbol]['price_history']) > self.lookback * 2:
                    self.coins_data[symbol]['price_history'].pop(0)

            # Update volume history
            if 'volume_24h' in data:
                volume = float(data['volume_24h'])
                self.coins_data[symbol]['volume_history'].append(volume)
                if len(self.coins_data[symbol]['volume_history']) > self.lookback * 2:
                    self.coins_data[symbol]['volume_history'].pop(0)

        return None

    def extract_base_symbol(self, symbol: str) -> str:
        """Extract the base cryptocurrency symbol from various formats"""
        # Handle symbols like BTC-USDT, BTCUSDT, etc.
        if '-' in symbol:
            # For BTC-USDT, return BTC
            return symbol.split('-')[0]
        elif len(symbol) > 3 and symbol.endswith(('USDT', 'USD', 'BTC', 'ETH', 'BNB')):
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

    def is_coin_excluded(self, coin_data: Dict) -> bool:
        """Check if a coin should be excluded based on configuration"""
        symbol = coin_data.get('symbol', '').upper()
        return symbol in self.excluded_coins

    def is_stablecoin(self, coin_data: Dict) -> bool:
        """Check if a coin is a stablecoin using multiple criteria"""
        symbol = coin_data.get('symbol', '')
        price = coin_data.get('price', 0)
        tags = coin_data.get('tags', [])

        # A) Tag-based filter
        for tag in self.stablecoin_tags:
            if tag in tags:
                return True

        # B) Price-based filter (around $1)
        if 0.95 < price < 1.05:
            return True

        # C) Known stablecoin blacklist
        if symbol in self.stablecoin_symbols:
            return True

        # Additional checks for common stablecoin characteristics
        # Some stablecoins might have slightly different prices
        if 0.90 < price < 1.10 and any(stable_name in symbol.lower() for stable_name in ['ust', 'lusd', 'alusd', 'busd']):
            return True

        return False

    def check_growth_potential(self, coin_data: Dict) -> Tuple[bool, List[str]]:
        """Check if a coin qualifies as high-growth potential"""
        reasons = []
        is_growth = True

        # A) Price Momentum - 24h change > 15%
        change_24h = coin_data.get('percent_change_24h', 0)
        if change_24h > self.growth_filters['min_24h_change']:
            reasons.append(f"24h change {change_24h:.2f}% > {self.growth_filters['min_24h_change']}%")
        else:
            is_growth = False
            reasons.append(f"24h change {change_24h:.2f}% <= {self.growth_filters['min_24h_change']}%")

        # B) High Trading Volume - volume_24h > 5,000,000
        volume_24h = coin_data.get('volume_24h', 0)
        if volume_24h > self.growth_filters['min_volume_24h']:
            reasons.append(f"Volume {volume_24h:,.0f} > {self.growth_filters['min_volume_24h']:,}")
        else:
            is_growth = False
            reasons.append(f"Volume {volume_24h:,.0f} <= {self.growth_filters['min_volume_24h']:,}")

        # C) Market Capitalization - <= 1,000,000,000 and > 10,000,000
        market_cap = coin_data.get('market_cap', 0)
        if market_cap <= self.growth_filters['max_market_cap'] and market_cap > self.growth_filters['min_market_cap']:
            reasons.append(f"Market cap {market_cap:,.0f} in range ({self.growth_filters['min_market_cap']:,}, {self.growth_filters['max_market_cap']:,}]")
        else:
            is_growth = False
            reasons.append(f"Market cap {market_cap:,.0f} outside range ({self.growth_filters['min_market_cap']:,}, {self.growth_filters['max_market_cap']:,}]")

        # D) Volatility - high_24h - low_24h >= 6% (we'll estimate from change data)
        # If we don't have high/low, we can use 24h change as a proxy for volatility
        volatility_proxy = abs(change_24h) / 100  # Convert percentage to ratio
        if volatility_proxy >= self.growth_filters['min_volatility']:
            reasons.append(f"Volatility proxy {volatility_proxy:.3f} >= {self.growth_filters['min_volatility']}")
        else:
            is_growth = False
            reasons.append(f"Volatility proxy {volatility_proxy:.3f} < {self.growth_filters['min_volatility']}")

        # E) Liquidity Health - volume_24h / market_cap >= 0.08
        liquidity_ratio = volume_24h / market_cap if market_cap > 0 else 0
        if liquidity_ratio >= self.growth_filters['min_liquidity_ratio']:
            reasons.append(f"Liquidity ratio {liquidity_ratio:.4f} >= {self.growth_filters['min_liquidity_ratio']}")
        else:
            is_growth = False
            reasons.append(f"Liquidity ratio {liquidity_ratio:.4f} < {self.growth_filters['min_liquidity_ratio']}")

        # Optional F) Trend Confirmation (would require historical MA data)
        # For now, we can use price momentum as a proxy
        if change_24h > 0:
            reasons.append("Positive momentum")

        return is_growth, reasons

    def check_crash_risk(self, coin_data: Dict) -> Tuple[bool, List[str]]:
        """Check if a coin qualifies as high-crash risk"""
        reasons = []
        is_crash_risk = True

        # A) Price Collapse - 24h change < -15%
        change_24h = coin_data.get('percent_change_24h', 0)
        if change_24h < self.crash_filters['max_24h_change']:
            reasons.append(f"24h change {change_24h:.2f}% < {self.crash_filters['max_24h_change']}%")
        else:
            is_crash_risk = False
            reasons.append(f"24h change {change_24h:.2f}% >= {self.crash_filters['max_24h_change']}%")

        # B) High Volume Confirmation - volume_24h > 2,000,000
        volume_24h = coin_data.get('volume_24h', 0)
        if volume_24h > self.crash_filters['min_volume_24h']:
            reasons.append(f"Volume {volume_24h:,.0f} > {self.crash_filters['min_volume_24h']:,}")
        else:
            is_crash_risk = False
            reasons.append(f"Volume {volume_24h:,.0f} <= {self.crash_filters['min_volume_24h']:,}")

        # D) High Volatility - (high_24h - low_24h) / price > 0.07
        # Using 24h change as proxy for volatility
        volatility_proxy = abs(change_24h) / 100  # Convert percentage to ratio
        if volatility_proxy > self.crash_filters['high_volatility_threshold']:
            reasons.append(f"Volatility proxy {volatility_proxy:.3f} > {self.crash_filters['high_volatility_threshold']}")
        else:
            is_crash_risk = False
            reasons.append(f"Volatility proxy {volatility_proxy:.3f} <= {self.crash_filters['high_volatility_threshold']}")

        # Additional check: If it's dropping significantly with high volume, it's concerning
        if change_24h < -20 and volume_24h > 5_000_000:
            reasons.append("Significant drop with high volume indicates panic selling")

        return is_crash_risk, reasons

    def screen_coins(self, limit: int = 50) -> Dict[str, Dict]:
        """Screen multiple coins and identify high-growth and high-crash risk coins"""
        logger.info("Starting CMC coin screening...")

        # Fetch top coins
        all_coins = self.fetch_all_cryptocurrencies(limit)
        if not all_coins:
            logger.error("Could not fetch cryptocurrency listings from CMC")
            return {}

        screening_results = {}

        for coin in all_coins:
            coin_symbol = coin['symbol']
            coin_name = coin['name']

            # Combine the coin data with quote data
            coin_data = {
                'symbol': coin_symbol,
                'name': coin_name,
                'rank': coin.get('cmc_rank', 0),
                'price': coin.get('quote', {}).get('USD', {}).get('price', 0),
                'market_cap': coin.get('quote', {}).get('USD', {}).get('market_cap', 0),
                'volume_24h': coin.get('quote', {}).get('USD', {}).get('volume_24h', 0),
                'percent_change_1h': coin.get('quote', {}).get('USD', {}).get('percent_change_1h', 0),
                'percent_change_24h': coin.get('quote', {}).get('USD', {}).get('percent_change_24h', 0),
                'percent_change_7d': coin.get('quote', {}).get('USD', {}).get('percent_change_7d', 0),
                'last_updated': coin.get('quote', {}).get('USD', {}).get('last_updated'),
                'tags': coin.get('tags', []),
            }

            # Skip if it's in the excluded list
            if self.is_coin_excluded(coin_data):
                continue

            # Skip if it's a stablecoin
            if self.is_stablecoin(coin_data):
                continue

            # Check for growth potential
            is_growth, growth_reasons = self.check_growth_potential(coin_data)

            # Check for crash risk
            is_crash_risk, crash_reasons = self.check_crash_risk(coin_data)

            # Store results
            screening_results[coin_symbol] = {
                'name': coin_name,
                'data': coin_data,
                'is_growth_potential': is_growth,
                'is_crash_risk': is_crash_risk,
                'growth_reasons': growth_reasons,
                'crash_reasons': crash_reasons
            }

        logger.info(f"Screening complete for {len(screening_results)} coins (excluding stablecoins)")
        self.screening_results = screening_results
        return screening_results

    def get_high_growth_coins(self) -> List[Dict]:
        """Get coins identified as high-growth potential"""
        high_growth_coins = []
        for symbol, data in self.screening_results.items():
            if data['is_growth_potential']:
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
            if data['is_crash_risk']:
                high_crash_coins.append({
                    'symbol': symbol,
                    'name': data['name'],
                    'data': data['data'],
                    'reasons': data['crash_reasons']
                })
        return high_crash_coins

    def analyze(self, symbol: Symbol = None) -> Optional[Signal]:
        """Analyze market conditions and return a signal based on screening results"""
        # For comprehensive screening, run the screening process
        if self.symbol == "ALL":
            screening_results = self.screen_coins(limit=100)  # Screen top 100 coins

            # Determine overall market sentiment based on screening
            growth_coins = self.get_high_growth_coins()
            crash_coins = self.get_high_crash_risk_coins()

            # If we have specific symbol to analyze, return its specific signal
            if symbol:
                symbol_str = symbol.value.split('-')[0] if '-' in symbol.value else symbol.value
                if symbol_str in screening_results:
                    result = screening_results[symbol_str]
                    return self._create_signal_for_coin(result, symbol)

            # Otherwise, return a general market signal based on overall screening
            return self._create_overall_market_signal(growth_coins, crash_coins, symbol or Symbol("BTC-USDT"))

        else:
            # For single symbol analysis (backward compatibility)
            cmc_data = self.fetch_cmc_data(symbol.value if symbol else self.symbol)
            if not cmc_data:
                logger.warning(f"Could not fetch CMC data for {symbol.value if symbol else self.symbol}")
                return None

            # Skip if it's in the excluded list
            if self.is_coin_excluded(cmc_data):
                logger.info(f"Skipping excluded coin: {cmc_data['symbol']}")
                return None

            # Skip if it's a stablecoin
            if self.is_stablecoin(cmc_data):
                logger.info(f"Skipping stablecoin: {cmc_data['symbol']}")
                return None

            # Check if the coin matches our criteria
            is_growth, growth_reasons = self.check_growth_potential(cmc_data)
            is_crash_risk, crash_reasons = self.check_crash_risk(cmc_data)

            result = {
                'name': cmc_data.get('name', ''),
                'data': cmc_data,
                'is_growth_potential': is_growth,
                'is_crash_risk': is_crash_risk,
                'growth_reasons': growth_reasons,
                'crash_reasons': crash_reasons
            }

            return self._create_signal_for_coin(result, symbol)

    def _create_signal_for_coin(self, result: Dict, symbol: Symbol) -> Optional[Signal]:
        """Create a signal for a specific coin based on screening results"""
        if result['is_growth_potential'] and not result['is_crash_risk']:
            # High growth potential, low crash risk
            signal_type = SignalType.BUY
            confidence = min(1.0, 0.7 + len(result['growth_reasons']) * 0.05)  # Higher confidence with more reasons
            score = 0.8
            reason = f"High growth potential: {', '.join(result['growth_reasons'][:2])}"  # Limit reasons in message
        elif result['is_crash_risk'] and not result['is_growth_potential']:
            # High crash risk, no growth potential
            signal_type = SignalType.SELL
            confidence = min(1.0, 0.7 + len(result['crash_reasons']) * 0.05)  # Higher confidence with more reasons
            score = -0.8
            reason = f"High crash risk: {', '.join(result['crash_reasons'][:2])}"  # Limit reasons in message
        elif result['is_growth_potential'] and result['is_crash_risk']:
            # Both high growth and high risk - likely very volatile
            signal_type = SignalType.HOLD
            confidence = 0.6
            score = 0.0
            reason = f"High volatility: Growth potential and crash risk detected"
        else:
            # Neither high growth nor high crash risk
            signal_type = SignalType.HOLD
            confidence = 0.3
            score = 0.0
            reason = "Neither growth nor crash characteristics detected"

        signal = Signal(
            symbol=str(symbol),
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy=self.name,
            timestamp=datetime.now(),
            metadata={
                'reason': reason,
                'is_growth': result['is_growth_potential'],
                'is_crash_risk': result['is_crash_risk'],
                'growth_reasons': result['growth_reasons'],
                'crash_reasons': result['crash_reasons'],
                'coin_data': result['data']
            }
        )

        logger.debug(f"CMCScreenerWatcher {self.name} generated signal for {result['data']['symbol']}: "
                    f"{signal_type} with score {score:.3f}, conf: {confidence:.3f}")

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            return signal

        return signal

    def _create_overall_market_signal(self, growth_coins: List[Dict], crash_coins: List[Dict], symbol: Symbol) -> Optional[Signal]:
        """Create an overall market signal based on screening results"""
        total_screened = len(self.screening_results)

        if total_screened == 0:
            return None

        growth_ratio = len(growth_coins) / total_screened
        crash_ratio = len(crash_coins) / total_screened

        if growth_ratio > 0.3:  # More than 30% show growth potential
            signal_type = SignalType.BUY
            confidence = min(0.9, 0.4 + growth_ratio)
            score = min(0.8, growth_ratio * 2)
            reason = f"Market bullish: {len(growth_coins)} of {total_screened} coins show growth potential"
        elif crash_ratio > 0.2:  # More than 20% show crash risk
            signal_type = SignalType.SELL
            confidence = min(0.9, 0.4 + crash_ratio)
            score = max(-0.8, -crash_ratio * 3)
            reason = f"Market bearish: {len(crash_coins)} of {total_screened} coins show crash risk"
        else:
            signal_type = SignalType.HOLD
            confidence = 0.5
            score = 0.0
            reason = f"Market neutral: {len(growth_coins)} growth, {len(crash_coins)} crash-risk coins"

        signal = Signal(
            symbol=str(symbol),
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy=self.name,
            timestamp=datetime.now(),
            metadata={
                'reason': reason,
                'total_screened': total_screened,
                'growth_coins_count': len(growth_coins),
                'crash_coins_count': len(crash_coins),
                'growth_ratio': growth_ratio,
                'crash_ratio': crash_ratio
            }
        )

        logger.debug(f"CMCScreenerWatcher {self.name} generated overall market signal: "
                    f"{signal_type} with score {score:.3f}, conf: {confidence:.3f}")

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            return signal

        return signal

    def get_screening_report(self) -> Dict[str, any]:
        """Get a comprehensive screening report"""
        growth_coins = self.get_high_growth_coins()
        crash_coins = self.get_high_crash_risk_coins()

        return {
            'total_coins_screened': len(self.screening_results),
            'high_growth_coins': len(growth_coins),
            'high_crash_risk_coins': len(crash_coins),
            'top_growth_coins': growth_coins[:5],  # Top 5 growth
            'top_crash_risk_coins': crash_coins[:5],  # Top 5 crash risk
            'screening_timestamp': datetime.now().isoformat()
        }

    def get_cmc_metrics(self) -> Dict:
        """Get current CMC metrics (backward compatibility)"""
        # Use metrics from screening results if available, otherwise defaults
        if self.symbol in self.screening_results:
            result = self.screening_results.get(self.symbol, {})
            coin_data = result.get('data', {})

            return {
                'current_rank': coin_data.get('rank', 0),
                'current_market_cap': coin_data.get('market_cap', 0),
                'current_price': coin_data.get('price', 0),
                'current_volume': coin_data.get('volume_24h', 0),
                'volume_score': 0,  # Placeholder - would need historical data
                'rank_trend': 0,    # Placeholder - would need historical data
                'regime': 'unknown',
                'data_points': 1,   # Placeholder
                'rank_change': 0    # Placeholder
            }
        else:
            # Fallback for single symbol analysis
            # If it's been updated, get data from coins_data
            if self.symbol in self.coins_data:
                coin_data = self.coins_data[self.symbol]
                price_history = coin_data.get('price_history', [])
                rank_history = coin_data.get('rank_history', [])

                current_price = price_history[-1] if price_history else 0
                current_rank = rank_history[-1] if rank_history else 0

                # Calculate simple metrics
                volume_score = 0
                if len(coin_data.get('volume_history', [])) >= 2:
                    current_vol = coin_data['volume_history'][-1]
                    avg_vol = sum(coin_data['volume_history'][:-1]) / max(1, len(coin_data['volume_history']) - 1)
                    volume_score = (current_vol - avg_vol) / max(avg_vol, 1)

                return {
                    'current_rank': current_rank,
                    'current_market_cap': coin_data['market_cap_history'][-1] if coin_data.get('market_cap_history') else 0,
                    'current_price': current_price,
                    'current_volume': coin_data['volume_history'][-1] if coin_data.get('volume_history') else 0,
                    'volume_score': volume_score,
                    'rank_trend': 0,  # Would need trend calculation
                    'regime': 'unknown',
                    'data_points': len(price_history),
                    'rank_change': current_rank - (rank_history[-2] if len(rank_history) > 1 else current_rank)
                }
            else:
                # Default return values
                return {
                    'current_rank': 0,
                    'current_market_cap': 0,
                    'current_price': 0,
                    'current_volume': 0,
                    'volume_score': 0,
                    'rank_trend': 0,
                    'regime': 'unknown',
                    'data_points': 0,
                    'rank_change': 0
                }