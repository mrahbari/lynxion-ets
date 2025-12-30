"""
Multi-Broker Service for handling exchange switching and symbol availability checks.
This service provides exchange switching capabilities similar to the downloader's approach.
"""
from typing import Dict, List, Optional, Set
from domain.entities.trading_entities import Order
from domain.ports.execution_ports import ExecutionPort
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from infrastructure.brokers.broker_adapters import (
    BingXBrokerAdapter, BinanceBrokerAdapter, MEXCBrokerAdapter, PhemexBrokerAdapter
)
from infrastructure.brokers.symbol_format_helper import SymbolFormatHelper
import os


class MultiBrokerExecutionService(ExecutionPort):
    """
    Multi-broker execution service that can switch between exchanges when one doesn't have a symbol.
    Implements exchange switching similar to the downloader's approach.
    """

    def __init__(self, primary_broker: Optional[str] = None):
        self.logger = EnhancedLogger("MultiBrokerExecutionService")

        # Initialize all broker adapters
        self.brokers = {}
        self._initialize_brokers()

        # Determine primary broker
        if primary_broker:
            self.primary_broker = primary_broker.lower()
        else:
            self.primary_broker = os.getenv('DEFAULT_BROKER', 'bingx').lower()  # Default to bingx as requested

        # Define the order of exchanges to try for symbol availability
        all_exchanges = [self.primary_broker, "binance", "bingx", "mexc", "phemex"]

        # Remove duplicates while preserving order and only include available brokers
        seen = set()
        self.exchange_order = []
        for ex in all_exchanges:
            if ex not in seen and ex in self.brokers:
                self.exchange_order.append(ex)
                seen.add(ex)

        # If primary broker is not in the list (shouldn't happen), add it at the beginning
        if self.primary_broker not in self.exchange_order and self.primary_broker in self.brokers:
            self.exchange_order.insert(0, self.primary_broker)

    def _initialize_brokers(self):
        """Initialize all available broker adapters."""
        # Initialize Binance
        try:
            binance_config = {
                'api_key': os.getenv('BINANCE_API_KEY'),
                'secret_key': os.getenv('BINANCE_SECRET_KEY'),
                'testnet': os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
            }
            if binance_config['api_key'] and binance_config['secret_key']:
                self.brokers['binance'] = BinanceBrokerAdapter(
                    api_key=binance_config['api_key'],
                    secret_key=binance_config['secret_key']
                )
                self.logger.info("✅ Binance broker initialized")
            else:
                self.logger.warning("⚠️ Binance broker not configured (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Binance broker: {e}")
        
        # Initialize BingX
        try:
            bingx_config = {
                'api_key': os.getenv('BINGX_API_KEY'),
                'secret_key': os.getenv('BINGX_SECRET_KEY'),
                'passphrase': os.getenv('BINGX_PASSPHRASE', ''),
                'testnet': os.getenv('BINGX_TESTNET', 'true').lower() == 'true'
            }
            required_keys = ['api_key', 'secret_key']
            if all(bingx_config.get(key) for key in required_keys):
                self.brokers['bingx'] = BingXBrokerAdapter(bingx_config)
                self.logger.info("✅ BingX broker initialized")
            else:
                self.logger.warning("⚠️ BingX broker not configured (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize BingX broker: {e}")
        
        # Initialize MEXC
        try:
            mexc_config = {
                'api_key': os.getenv('MEXC_API_KEY'),
                'secret_key': os.getenv('MEXC_SECRET_KEY'),
                'testnet': os.getenv('MEXC_TESTNET', 'true').lower() == 'true'
            }
            required_keys = ['api_key', 'secret_key']
            if all(mexc_config.get(key) for key in required_keys):
                self.brokers['mexc'] = MEXCBrokerAdapter(mexc_config)
                self.logger.info("✅ MEXC broker initialized")
            else:
                self.logger.warning("⚠️ MEXC broker not configured (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize MEXC broker: {e}")
        
        # Initialize Phemex
        try:
            phemex_config = {
                'api_key': os.getenv('PHEMEX_API_KEY'),
                'secret_key': os.getenv('PHEMEX_SECRET_KEY'),
                'testnet': os.getenv('PHEMEX_TESTNET', 'true').lower() == 'true'
            }
            required_keys = ['api_key', 'secret_key']
            if all(phemex_config.get(key) for key in required_keys):
                self.brokers['phemex'] = PhemexBrokerAdapter(phemex_config)
                self.logger.info("✅ Phemex broker initialized")
            else:
                self.logger.warning("⚠️ Phemex broker not configured (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Phemex broker: {e}")

    def get_available_symbols(self) -> Set[str]:
        """
        Get available symbols from all configured brokers.
        This aggregates symbols from all available exchanges.
        """
        all_symbols = set()
        
        for exchange_name, broker in self.brokers.items():
            try:
                if hasattr(broker, 'get_available_symbols'):
                    symbols = broker.get_available_symbols()
                    all_symbols.update(symbols)
                    self.logger.debug(f"Got {len(symbols)} symbols from {exchange_name}")
            except Exception as e:
                self.logger.warning(f"Could not get symbols from {exchange_name}: {e}")
        
        return all_symbols

    def is_symbol_available(self, symbol: str) -> bool:
        """
        Check if a symbol is available on any of the configured exchanges.
        """
        for exchange_name in self.exchange_order:
            broker = self.brokers.get(exchange_name)
            if broker and hasattr(broker, 'get_available_symbols'):
                try:
                    available_symbols = broker.get_available_symbols()
                    if symbol in available_symbols:
                        self.logger.debug(f"Symbol {symbol} found on {exchange_name}")
                        return True
                except Exception as e:
                    self.logger.warning(f"Error checking symbol {symbol} on {exchange_name}: {e}")
                    continue
        
        # If not found through broker methods, try direct API check
        return self._check_symbol_direct_api(symbol)

    def _check_symbol_direct_api(self, symbol: str) -> bool:
        """
        Fallback method to check symbol availability via direct API calls.
        """
        import requests
        
        # Try each exchange via direct API
        for exchange_name in self.exchange_order:
            try:
                if exchange_name == 'binance':
                    api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                elif exchange_name == 'bingx':
                    api_url = f"https://open-api-vst.bingx.com/openApi/quote/v1/ticker/price?symbol={SymbolFormatHelper.format_symbol_for_exchange(symbol, exchange_name)}"
                elif exchange_name == 'mexc':
                    api_url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
                elif exchange_name == 'phemex':
                    api_url = f"https://api.phemex.com/md/ticker/24hr?symbol={symbol}"
                else:
                    continue  # Skip unknown exchanges
                
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    # Check if the response contains valid price data
                    data = response.json()
                    if 'price' in data or ('data' in data and 'last' in data.get('data', {})):
                        self.logger.debug(f"Symbol {symbol} found via direct API on {exchange_name}")
                        return True
            except Exception as e:
                self.logger.debug(f"Direct API check failed for {symbol} on {exchange_name}: {e}")
                continue
        
        return False

    def execute_order(self, order: Order) -> str:
        """
        Execute an order, trying different exchanges if the symbol is not available on the primary one.
        """
        symbol_str = order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol)
        
        # Find the best exchange for this symbol
        best_exchange = self._find_best_exchange_for_symbol(symbol_str)
        
        if best_exchange:
            broker = self.brokers[best_exchange]
            self.logger.info(f"🎯 EXECUTING ORDER ON {best_exchange.upper()}: {order}")
            
            try:
                order_id = broker.place_order(order)
                self.logger.info(f"✅ ORDER PLACED SUCCESSFULLY ON {best_exchange.upper()}: {order_id}")
                return order_id
            except Exception as e:
                self.logger.error(f"❌ FAILED TO EXECUTE ORDER ON {best_exchange.upper()}: {e}")
                raise
        else:
            raise Exception(f"Symbol {symbol_str} not available on any configured exchange")

    def _find_best_exchange_for_symbol(self, symbol: str) -> Optional[str]:
        """
        Find the best exchange for a given symbol by checking availability.
        """
        # First, try to find an exchange where the symbol is available
        for exchange_name in self.exchange_order:
            broker = self.brokers.get(exchange_name)
            if broker and hasattr(broker, 'get_available_symbols'):
                try:
                    available_symbols = broker.get_available_symbols()
                    if symbol in available_symbols:
                        self.logger.debug(f"Found {symbol} on {exchange_name}")
                        return exchange_name
                except Exception as e:
                    self.logger.warning(f"Error checking {symbol} on {exchange_name}: {e}")
                    continue
        
        # If not found through broker methods, try direct API check
        for exchange_name in self.exchange_order:
            if self._check_symbol_direct_api_on_exchange(symbol, exchange_name):
                self.logger.debug(f"Confirmed {symbol} available on {exchange_name} via direct API")
                return exchange_name
        
        # If symbol is not found on any exchange, return None
        self.logger.warning(f"Symbol {symbol} not found on any configured exchange")
        return None

    def _check_symbol_direct_api_on_exchange(self, symbol: str, exchange_name: str) -> bool:
        """
        Check if a symbol is available on a specific exchange via direct API.
        """
        import requests
        
        try:
            if exchange_name == 'binance':
                api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            elif exchange_name == 'bingx':
                formatted_symbol = SymbolFormatHelper.format_symbol_for_exchange(symbol, exchange_name)
                api_url = f"https://open-api-vst.bingx.com/openApi/quote/v1/ticker/price?symbol={formatted_symbol}"
            elif exchange_name == 'mexc':
                api_url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
            elif exchange_name == 'phemex':
                api_url = f"https://api.phemex.com/md/ticker/24hr?symbol={symbol}"
            else:
                return False
            
            response = requests.get(api_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order - this is more complex as we need to know which exchange the order was placed on.
        For now, we'll try to cancel on all exchanges.
        """
        results = []
        for exchange_name, broker in self.brokers.items():
            try:
                # We need to pass a symbol, but we don't know which symbol was used for the order
                # This is a limitation - in a real system, order tracking would store exchange info
                # For now, we'll return False as we can't properly cancel without knowing the exchange
                self.logger.warning(f"Cannot cancel order {order_id} without knowing original exchange")
                return False
            except Exception as e:
                self.logger.error(f"Error canceling order {order_id} on {exchange_name}: {e}")
                results.append(False)
        
        return any(results)

    def get_execution_status(self, execution_id: str) -> str:
        """
        Get execution status - similar issue as cancel_order, we need to know which exchange.
        """
        # This is complex without order tracking - return unknown status
        self.logger.warning(f"Cannot get status for execution {execution_id} without knowing original exchange")
        return "unknown"