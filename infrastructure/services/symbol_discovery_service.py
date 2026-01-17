"""
Symbol Discovery Module for Market Opportunity Watcher
Handles automatic discovery of symbols based on market conditions and watcher requirements
"""
import os
import ccxt
import requests
from typing import List
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger


class SymbolDiscoveryService:
    """Service class for discovering symbols to monitor based on various market conditions."""
    
    def __init__(self, logger: EnhancedLogger = None):
        self.logger = logger or EnhancedLogger("SymbolDiscoveryService")
    
    def discover_symbols_automatically(self) -> List[Symbol]:
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

        # When multiple watchers are enabled, we want to ensure comprehensive coverage
        # Rather than choosing one discovery method, we should combine results from multiple discovery methods
        # to ensure symbols relevant to all watcher types are included
        watcher_specific_symbols = {}
        all_discovered_symbols = set()

        # Add symbols from each enabled watcher type's specific discovery method
        for watcher_type in enabled_watchers:
            if watcher_type == 'market_pulse':
                symbols = self.discover_trend_oriented_symbols()  # Use appropriate discovery method
            elif watcher_type == 'volatility':
                symbols = self.discover_volatility_oriented_symbols()
            elif watcher_type == 'trend_mtf':
                symbols = self.discover_trend_oriented_symbols()
            elif watcher_type == 'anomaly_ml':
                symbols = self.discover_anomaly_oriented_symbols()
            elif watcher_type == 'orderflow_ws':
                symbols = self.discover_orderflow_oriented_symbols()
            elif watcher_type == 'funding_rate':
                symbols = self.discover_funding_oriented_symbols()
            elif watcher_type == 'liquidity':
                symbols = self.discover_liquidity_oriented_symbols()
            elif watcher_type == 'historical_candle':
                symbols = self.discover_historical_candle_oriented_symbols()
            elif watcher_type == 'cmc_screener':
                symbols = self.discover_by_market_cap()
            elif watcher_type == 'tick_watcher':
                symbols = self.discover_tick_oriented_symbols()
            else:
                symbols = self.discover_by_market_cap()

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
        general_symbols = self.discover_by_market_cap()
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

        # Log the combined symbol set
        self.logger.info(
            f"📊 COMBINED SYMBOLS: {len(discovered_symbols)} total symbols after combining {len(enabled_watchers)} watcher types",
            total_symbols=len(discovered_symbols),
            watcher_count=len(enabled_watchers),
            watcher_specific=watcher_specific_symbols)

        # If no specific discovery method worked, fall back to price activity
        if not discovered_symbols:
            price_activity_symbols = self.discover_by_price_activity()
            if price_activity_symbols:
                discovered_symbols = price_activity_symbols

                # Add price activity symbols to the cmc_screener category and log them
                if 'cmc_screener' in watcher_specific_symbols:
                    watcher_specific_symbols['cmc_screener'].extend(price_activity_symbols)

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
            if fallback_symbols and 'cmc_screener' in watcher_specific_symbols:
                watcher_specific_symbols['cmc_screener'].extend(fallback_symbols)

                # Log the fallback symbols that were added
                self.logger.info(
                    f"🔍 CMC SCREENER DISCOVERED: {len(fallback_symbols)} fallback symbols - {fallback_symbols[:5]}{'...' if len(fallback_symbols) > 5 else ''}",
                    watcher_type='cmc_screener',
                    symbols_discovered=len(fallback_symbols),
                    sample_symbols=fallback_symbols[:5])

        # Filter out stablecoin-to-stablecoin pairs (e.g., USDTUSDT, USDCUSDT, etc.)
        from .symbol_validation_service import SymbolValidationService
        validation_service = SymbolValidationService(self.logger)
        filtered_symbols = validation_service.filter_stablecoin_pairs(discovered_symbols)

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

    def discover_trend_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with strong trend characteristics for trend watchers"""
        try:
            # This would connect to exchange APIs to get trending symbols
            # For now, we'll simulate by finding symbols with strong directional moves
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

    def discover_volatility_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with volatility opportunities for volatility watchers"""
        try:
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

    def discover_momentum_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with momentum opportunities for market pulse watchers"""
        try:
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

    def discover_anomaly_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with unusual patterns for anomaly watchers"""
        try:
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

    def discover_orderflow_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with significant order flow for order flow watchers"""
        try:
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

    def discover_liquidity_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with liquidity opportunities for liquidity watchers"""
        try:
            exchange = ccxt.binance()
            tickers = exchange.fetch_tickers()

            # Find symbols with high volume and tight spreads (good liquidity conditions)
            liquid_symbols = []
            for symbol, ticker in tickers.items():
                if (symbol.endswith('/USDT') and
                        'quoteVolume' in ticker and ticker['quoteVolume'] and
                        'high' in ticker and 'low' in ticker and ticker['high'] and ticker['low']):

                    # Look for symbols with high volume and relatively tight volatility (good liquidity conditions)
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

    def discover_funding_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with significant funding rate opportunities for funding rate watchers"""
        try:
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
            return self.discover_by_market_cap()

    def discover_by_market_cap(self) -> List[Symbol]:
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

    def discover_by_price_activity(self) -> List[Symbol]:
        """Discover symbols based on price/volume activity from exchange data."""
        try:
            # This would connect to exchange APIs to get recent activity
            # For now, we'll simulate using a placeholder that would connect to exchange data
            # This could use ccxt or other exchange APIs to get recent price/volume spikes
            discovered_symbols = self.get_active_symbols_from_exchange()

            if discovered_symbols:
                return discovered_symbols[:10]  # Limit to top 10

            # If exchange-based discovery fails, return empty list and let fallback happen
            return []
        except Exception as e:
            self.logger.warning(f"Error during activity-based symbol discovery: {e}")
            return []

    def get_active_symbols_from_exchange(self) -> List[Symbol]:
        """Get active symbols from exchange based on volume and price changes."""
        # In a real implementation, this would connect to exchange APIs
        # to get recent symbols with high volume or price volatility
        try:
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

    def discover_historical_candle_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with reliable historical data for historical candle watchers."""
        try:
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
                historical_oriented_symbols = [Symbol(sym) for sym in major_symbols]

            return historical_oriented_symbols
        except Exception as e:
            self.logger.warning(f"Error in historical candle-oriented symbol discovery: {e}")
            # Fall back to general discovery if specific discovery fails
            return self.discover_by_market_cap()

    def discover_tick_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with high tick frequency and trading activity for tick watchers."""
        try:
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
            return self.discover_by_market_cap()