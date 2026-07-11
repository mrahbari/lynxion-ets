"""
Symbol Discovery Module for Market Opportunity Watcher
Handles automatic discovery of symbols based on market conditions and watcher requirements
"""
import ccxt
import requests
from typing import List
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger


class SymbolDiscoveryService:
    """Service class for discovering symbols to monitor based on various market conditions."""

    def __init__(self, settings, logger: EnhancedLogger = None):
        # Settings injected by the composition root (E1.T4); read the same fields
        # off self._settings instead of importing bootstrap.settings.loaders.
        self._settings = settings
        self.logger = logger or EnhancedLogger("SymbolDiscoveryService")
    
    def _get_exchange(self):
        """Resolve the default exchange object to fetch tickers/data from."""
        try:
            broker_name = self._settings.broker.default_broker.lower() if self._settings.broker and hasattr(self._settings.broker, 'default_broker') else 'binance'
            ccxt_name = broker_name
            
            if hasattr(ccxt, ccxt_name):
                self.logger.info(f"Using dynamic exchange CCXT.{ccxt_name} for symbol discovery")
                return getattr(ccxt, ccxt_name)({'enableRateLimit': True})
        except Exception as e:
            self.logger.warning(f"Error resolving dynamic exchange, falling back to CCXT.binance: {e}")
        return ccxt.binance({'enableRateLimit': True})

    def discover_symbols_automatically(self) -> List[Symbol]:
        """Dynamically discover symbols to monitor based on market conditions or other criteria."""
        self.logger.info("🔍 Discovering symbols to monitor automatically...")

        # Check which watcher types are enabled to determine appropriate discovery method
        market_pulse_enabled = self._settings.watcher.market_pulse_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'market_pulse_watcher_enabled') else True
        volatility_enabled = self._settings.watcher.volatility_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'volatility_watcher_enabled') else True
        trend_mtf_enabled = self._settings.watcher.trend_mtf_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'trend_mtf_watcher_enabled') else True
        anomaly_ml_enabled = self._settings.watcher.anomaly_ml_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'anomaly_ml_watcher_enabled') else True
        orderflow_ws_enabled = self._settings.watcher.orderflow_ws_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'orderflow_ws_watcher_enabled') else True
        cmc_screener_enabled = self._settings.watcher.cmc_screener_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'cmc_screener_enabled') else True
        funding_rate_enabled = self._settings.watcher.funding_rate_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'funding_rate_watcher_enabled') else True
        liquidity_enabled = self._settings.watcher.liquidity_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'liquidity_watcher_enabled') else True
        historical_candle_enabled = self._settings.watcher.historical_candle_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'historical_candle_watcher_enabled') else True
        tick_watcher_enabled = self._settings.watcher.tick_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'tick_watcher_enabled') else False

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
            fallback_symbols_str = self._settings.data.fallback_watchlist_symbols if self._settings.data and self._settings.data.fallback_watchlist_symbols else "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,AVAXUSDT,TRXUSDT,DOTUSDT,LINKUSDT"
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
        validation_service = SymbolValidationService(self.logger, data_config=self._settings.data)
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
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            trending_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if 'change' in ticker and ticker['change'] is not None:
                            change_abs = abs(ticker['change'])
                            if change_abs > 3.0 and ticker.get('quoteVolume') and ticker['quoteVolume'] > 1000000:
                                trending_symbols.append(valid_symbol)
                                if len(trending_symbols) >= 10:
                                    break
                except ValueError:
                    continue

            return trending_symbols
        except Exception as e:
            self.logger.warning(f"Error in trend-oriented symbol discovery: {e}")
            return []

    def discover_volatility_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with volatility opportunities for volatility watchers"""
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            volatile_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if ('high' in ticker and ticker['high'] is not None and
                                'low' in ticker and ticker['low'] is not None and
                                'open' in ticker and ticker['open'] is not None and
                                'quoteVolume' in ticker and ticker['quoteVolume'] is not None):
                            if ticker['open'] != 0:
                                volatility = abs((ticker['high'] - ticker['low']) / ticker['open']) * 100
                                if volatility > 5.0 and ticker['quoteVolume'] > 500000:
                                    volatile_symbols.append(valid_symbol)
                                    if len(volatile_symbols) >= 10:
                                        break
                except ValueError:
                    continue

            return volatile_symbols
        except Exception as e:
            self.logger.warning(f"Error in volatility-oriented symbol discovery: {e}")
            return []

    def discover_momentum_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with momentum opportunities for market pulse watchers"""
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            momentum_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if ('change' in ticker and ticker['change'] is not None and
                                'quoteVolume' in ticker and ticker['quoteVolume'] is not None):
                            if abs(ticker['change']) > 2.5 and ticker['quoteVolume'] > 2000000:
                                momentum_symbols.append(valid_symbol)
                                if len(momentum_symbols) >= 10:
                                    break
                except ValueError:
                    continue

            return momentum_symbols
        except Exception as e:
            self.logger.warning(f"Error in momentum-oriented symbol discovery: {e}")
            return []

    def discover_anomaly_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with unusual patterns for anomaly watchers"""
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            anomaly_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if ('change' in ticker and ticker['change'] is not None and
                                'high' in ticker and ticker['high'] is not None and
                                'low' in ticker and ticker['low'] is not None and
                                'open' in ticker and ticker['open'] is not None and
                                'quoteVolume' in ticker and ticker['quoteVolume'] is not None):
                            change_abs = abs(ticker['change'])
                            volatility = abs((ticker['high'] - ticker['low']) / ticker['open']) * 100 if ticker['open'] != 0 else 0
                            if change_abs > 4.0 and volatility > 6.0 and ticker['quoteVolume'] > 1000000:
                                anomaly_symbols.append(valid_symbol)
                                if len(anomaly_symbols) >= 10:
                                    break
                except ValueError:
                    continue

            return anomaly_symbols
        except Exception as e:
            self.logger.warning(f"Error in anomaly-oriented symbol discovery: {e}")
            return []

    def discover_orderflow_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with significant order flow for order flow watchers"""
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            high_volume_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if 'quoteVolume' in ticker and ticker['quoteVolume'] is not None:
                            if ticker['quoteVolume'] > 50000000:
                                high_volume_symbols.append(valid_symbol)
                                if len(high_volume_symbols) >= 10:
                                    break
                except ValueError:
                    continue

            return high_volume_symbols
        except Exception as e:
            self.logger.warning(f"Error in order flow-oriented symbol discovery: {e}")
            return []

    def discover_liquidity_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with liquidity opportunities for liquidity watchers"""
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            liquid_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if ('quoteVolume' in ticker and ticker['quoteVolume'] is not None and
                                'high' in ticker and ticker['high'] is not None and
                                'low' in ticker and ticker['low'] is not None):
                            if ticker['quoteVolume'] > 10000000 and ticker['high'] != 0:
                                volatility = abs((ticker['high'] - ticker['low']) / ticker['high']) * 100
                                if volatility < 8.0:
                                    liquid_symbols.append(valid_symbol)
                                    if len(liquid_symbols) >= 10:
                                        break
                except ValueError:
                    continue

            return liquid_symbols
        except Exception as e:
            self.logger.warning(f"Error in liquidity-oriented symbol discovery: {e}")
            return []

    def discover_funding_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with significant funding rate opportunities for funding rate watchers"""
        try:
            exchange = self._get_exchange()
            markets = exchange.load_markets()

            from .symbol_validator import symbol_validator
            perp_symbols = []
            for symbol, market in markets.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if market.get('swap', False) and market.get('active', True):
                            perp_symbols.append(valid_symbol)
                            if len(perp_symbols) >= 20:
                                break
                except ValueError:
                    continue

            return perp_symbols[:10]
        except Exception as e:
            self.logger.warning(f"Using fallback for funding-oriented discovery: {e}")
            return self.discover_by_market_cap()

    def discover_by_market_cap(self) -> List[Symbol]:
        """Discover symbols based on market cap from CMC API."""
        try:
            import requests
            import os
            from dotenv import load_dotenv
            load_dotenv()

            cmc_api_key = self._settings.data.cmc_api_key if self._settings.data and self._settings.data.cmc_api_key else None
            cmc_listings_url = self._settings.data.cmc_listings_url if self._settings.data and self._settings.data.cmc_listings_url else "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

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
                    excluded_coins_cfg = self._settings.data.cmc_excluded_coins if self._settings.data and self._settings.data.cmc_excluded_coins else "BTC,ETH,SOL,ADA,DOT,XRP,DOGE,LINK,BNB,AVAX,MATIC,BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT,DOTUSDT,XRPUSDT,DOGEUSDT,LINKUSDT,BNBUSDT,AVAXUSDT,MATICUSDT"
                    # cmc_excluded_coins may be configured as a comma-string OR a list; the
                    # old code assumed a string and called .split(',') -> crashed with
                    # "'list' object has no attribute 'split'". Handle both. (Type-A defect.)
                    excluded_iter = excluded_coins_cfg.split(',') if isinstance(excluded_coins_cfg, str) else excluded_coins_cfg
                    excluded_coins = set(str(coin).strip().upper() for coin in excluded_iter if str(coin).strip())

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
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            usdt_pairs = {}
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if 'quoteVolume' in ticker and ticker['quoteVolume'] is not None:
                            usdt_pairs[valid_symbol] = ticker['quoteVolume']
                except ValueError:
                    continue

            sorted_symbols = sorted(usdt_pairs.items(), key=lambda x: x[1], reverse=True)
            top_symbols = [pair for pair, volume in sorted_symbols[:10]]
            return top_symbols
        except Exception as e:
            self.logger.warning(f"Error getting active symbols from exchange: {e}")
            return []

    def discover_historical_candle_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with reliable historical data for historical candle watchers."""
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            historical_oriented_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if ('quoteVolume' in ticker and ticker['quoteVolume'] is not None and
                                'count' in ticker and ticker['count'] is not None and
                                'high' in ticker and ticker['high'] is not None and
                                'low' in ticker and ticker['low'] is not None):
                            volume = ticker['quoteVolume']
                            trade_count = ticker['count']
                            if volume > 5000000 and trade_count > 2000:
                                historical_oriented_symbols.append(valid_symbol)
                                if len(historical_oriented_symbols) >= 10:
                                    break
                except ValueError:
                    continue

            if len(historical_oriented_symbols) < 5:
                major_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
                                 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT']
                historical_oriented_symbols = [Symbol(sym) for sym in major_symbols if symbol_validator.is_symbol_approved(Symbol(sym))]

            return historical_oriented_symbols
        except Exception as e:
            self.logger.warning(f"Error in historical candle-oriented symbol discovery: {e}")
            return self.discover_by_market_cap()

    def discover_tick_oriented_symbols(self) -> List[Symbol]:
        """Discover symbols with high tick frequency and trading activity for tick watchers."""
        try:
            exchange = self._get_exchange()
            tickers = exchange.fetch_tickers()

            from .symbol_validator import symbol_validator
            tick_oriented_symbols = []
            for symbol, ticker in tickers.items():
                formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                try:
                    valid_symbol = Symbol(formatted_symbol)
                    if symbol_validator.is_symbol_approved(valid_symbol):
                        if ('quoteVolume' in ticker and ticker['quoteVolume'] is not None and
                                'count' in ticker and ticker['count'] is not None):
                            volume = ticker['quoteVolume']
                            trade_count = ticker['count']
                            if volume > 10000000 and trade_count > 5000:
                                tick_oriented_symbols.append(valid_symbol)
                                if len(tick_oriented_symbols) >= 10:
                                    break
                except ValueError:
                    continue

            if len(tick_oriented_symbols) < 5:
                high_volume_symbols = []
                for symbol, ticker in tickers.items():
                    formatted_symbol = symbol.replace('/', '').replace('-', '').upper()
                    try:
                        valid_symbol = Symbol(formatted_symbol)
                        if symbol_validator.is_symbol_approved(valid_symbol):
                            if 'quoteVolume' in ticker and ticker['quoteVolume'] is not None:
                                if ticker['quoteVolume'] > 20000000:
                                    high_volume_symbols.append(valid_symbol)
                                    if len(high_volume_symbols) >= 10:
                                        break
                    except ValueError:
                        continue
                tick_oriented_symbols = high_volume_symbols

            return tick_oriented_symbols
        except Exception as e:
            self.logger.warning(f"Error in tick-oriented symbol discovery: {e}")
            return self.discover_by_market_cap()