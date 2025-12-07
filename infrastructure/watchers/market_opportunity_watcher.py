"""
Market Opportunity Watcher for auto-detection system.
Monitors markets continuously and identifies opportunities based on technical conditions.
"""
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol
from infrastructure.watchers.watcher_adapters import (
    MarketPulseWatcherAdapter,
    VolatilityWatcherAdapter,
    TrendMTFWatcherAdapter,
    AnomalyMLWatcherAdapter,
    OrderFlowWatcherAdapter
)
from infrastructure.watchers.adapters.cmc_watcher_adapter import CMCWatcherAdapter, CMCScreenerAdapter
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
            # Default symbols to monitor if none provided and auto-discovery is off
            self.symbols = [Symbol("BTCUSDT"), Symbol("ETHUSDT"), Symbol("SOLUSDT"), Symbol("XRPUSDT")]

        # Initialize watcher adapters for each symbol
        self._initialize_watchers()

    def _discover_symbols_automatically(self) -> List[Symbol]:
        """Dynamically discover symbols to monitor based on market conditions or other criteria."""
        self.logger.info("🔍 Discovering symbols to monitor automatically...")

        try:
            # Try to use the CMCScreener to get a comprehensive list of symbols
            cmc_screener = CMCScreenerAdapter(name="CMCAutoDiscovery")

            # Get screening results using analyze method (which will screen top coins)
            # For auto-discovery of symbols, we'll fetch the top coins directly
            from decimal import Decimal
            import requests
            import os
            from dotenv import load_dotenv
            load_dotenv()

            cmc_api_key = os.getenv("CMC_API_KEY")
            cmc_listings_url = os.getenv("CMC_LISTINGS_URL", "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

            if not cmc_api_key:
                self.logger.warning("CMC_API_KEY not found, using default symbols")
                # Use default symbols if no CMC API key is available
                discovered_symbols = [
                    "BTCUSDT",  # Bitcoin - major trading pair
                    "ETHUSDT",  # Ethereum - major trading pair
                    "SOLUSDT",  # Solana - high volume altcoin
                    "XRPUSDT",  # Ripple - high volume altcoin
                    "ADAUSDT",  # Cardano - high volume altcoin
                    "DOGEUSDT", # Dogecoin - popular meme coin
                    "AVAXUSDT", # Avalanche - smart contract platform
                    "MATICUSDT", # Polygon - scaling solution
                    "DOTUSDT",  # Polkadot - interoperability
                    "LINKUSDT", # Chainlink - oracle network
                ]
            else:
                # Use the CMCScreenerAdapter's screening capability
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
                        # Extract symbols from the top 15 coins (excluding major coins that are typically excluded)
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
                    else:
                        self.logger.warning("CMC API returned no data, using defaults")
                        discovered_symbols = [
                            "BTCUSDT",  # Bitcoin - major trading pair
                            "ETHUSDT",  # Ethereum - major trading pair
                            "SOLUSDT",  # Solana - high volume altcoin
                            "XRPUSDT",  # Ripple - high volume altcoin
                            "ADAUSDT",  # Cardano - high volume altcoin
                            "DOGEUSDT", # Dogecoin - popular meme coin
                            "AVAXUSDT", # Avalanche - smart contract platform
                            "MATICUSDT", # Polygon - scaling solution
                            "DOTUSDT",  # Polkadot - interoperability
                            "LINKUSDT", # Chainlink - oracle network
                        ]
                except Exception as e:
                    self.logger.warning(f"Error fetching from CMC API: {e}. Using default symbols.")
                    discovered_symbols = [
                        "BTCUSDT",  # Bitcoin - major trading pair
                        "ETHUSDT",  # Ethereum - major trading pair
                        "SOLUSDT",  # Solana - high volume altcoin
                        "XRPUSDT",  # Ripple - high volume altcoin
                        "ADAUSDT",  # Cardano - high volume altcoin
                        "DOGEUSDT", # Dogecoin - popular meme coin
                        "AVAXUSDT", # Avalanche - smart contract platform
                        "MATICUSDT", # Polygon - scaling solution
                        "DOTUSDT",  # Polkadot - interoperability
                        "LINKUSDT", # Chainlink - oracle network
                    ]
        except Exception as e:
            self.logger.warning(f"Error during symbol discovery: {e}. Falling back to default symbols.")
            discovered_symbols = [
                "BTCUSDT",  # Bitcoin - major trading pair
                "ETHUSDT",  # Ethereum - major trading pair
                "SOLUSDT",  # Solana - high volume altcoin
                "XRPUSDT",  # Ripple - high volume altcoin
                "ADAUSDT",  # Cardano - high volume altcoin
                "DOGEUSDT", # Dogecoin - popular meme coin
                "AVAXUSDT", # Avalanche - smart contract platform
                "MATICUSDT", # Polygon - scaling solution
                "DOTUSDT",  # Polkadot - interoperability
                "LINKUSDT", # Chainlink - oracle network
            ]

        self.logger.info(f"✅ Auto-discovered {len(discovered_symbols)} symbols to monitor: {discovered_symbols}")
        return [Symbol(s) for s in discovered_symbols]

    def _update_symbol_list(self):
        """Dynamically update the list of symbols to monitor based on market conditions."""
        if not self.auto_discover_symbols:
            return  # Only update if auto-discovery is enabled

        # In a real system, this would run periodically to re-evaluate which symbols to watch
        # For example, identifying symbols with sudden volatility spikes, increased volume, etc.
        current_symbols = [s.value for s in self.symbols]
        new_symbols = self._discover_symbols_automatically()
        new_symbol_values = [s.value for s in new_symbols]

        if current_symbols != new_symbol_values:
            self.logger.info(f"🔄 Symbol list updated: {current_symbols} -> {new_symbol_values}")
            # Here we would need to reinitialize watchers for new symbols
            removed_symbols = set(current_symbols) - set(new_symbol_values)
            added_symbols = set(new_symbol_values) - set(current_symbols)

            if removed_symbols:
                self.logger.info(f"🗑️ Symbols removed: {removed_symbols}")
            if added_symbols:
                self.logger.info(f"🆕 New symbols added: {added_symbols}")
                # Add watchers for new symbols
                for symbol_str in added_symbols:
                    symbol = Symbol(symbol_str)
                    self.symbols.append(symbol)
                    self.watchers[symbol_str] = {
                        'market_pulse': MarketPulseWatcherAdapter(symbol),
                        'volatility': VolatilityWatcherAdapter(symbol),
                        'trend_mtf': TrendMTFWatcherAdapter(symbol),
                        'anomaly_ml': AnomalyMLWatcherAdapter(symbol),
                        'order_flow': OrderFlowWatcherAdapter(symbol),
                        'cmc_watcher': CMCWatcherAdapter(symbol),
                    }
                    # Start new watchers
                    for watcher_name, watcher in self.watchers[symbol_str].items():
                        watcher.start()

            # Update symbol list
            self.symbols = new_symbols
        
    def _initialize_watchers(self):
        """Initialize watcher adapters for each symbol."""
        for symbol in self.symbols:
            self.watchers[symbol.value] = {
                'market_pulse': MarketPulseWatcherAdapter(symbol),
                'volatility': VolatilityWatcherAdapter(symbol),
                'trend_mtf': TrendMTFWatcherAdapter(symbol),
                'anomaly_ml': AnomalyMLWatcherAdapter(symbol),
                'order_flow': OrderFlowWatcherAdapter(symbol),
                'cmc_watcher': CMCWatcherAdapter(symbol),
            }
            # Start each watcher
            for watcher_name, watcher in self.watchers[symbol.value].items():
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
        """Analyze a symbol using all available watchers."""
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
        
        # Analyze with each watcher
        for watcher_name, watcher in self.watchers[symbol_str].items():
            signal = watcher.analyze(symbol)
            if signal:
                opportunities['signals'][watcher_name] = {
                    'signal_type': signal.signal_type.name,
                    'confidence': float(signal.confidence.value),
                    'score': signal.score,
                    'timestamp': signal.timestamp.isoformat(),
                    'metadata': signal.metadata
                }
                
                # Determine overall recommendation based on signals
                if signal.signal_type.name in ['BUY', 'SELL']:
                    opportunities['recommendation'] = signal.signal_type.name
                    opportunities['confidence'] = max(opportunities['confidence'], float(signal.confidence.value))
                    
                    # Suggest strategy based on signal type and characteristics
                    opportunities['strategy_suggestion'] = self._suggest_strategy_for_signal(signal)
                    
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