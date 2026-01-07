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
            mexc_api_key = os.getenv('MEXC_API_KEY')
            mexc_secret_key = os.getenv('MEXC_SECRET_KEY')
            mexc_testnet = os.getenv('MEXC_TESTNET', 'true').lower() == 'true'

            if mexc_api_key and mexc_secret_key:
                # Use testnet URL if testnet is enabled
                base_url = "https://api-testnet.mexc.com" if mexc_testnet else "https://api.mexc.com"
                self.brokers['mexc'] = MEXCBrokerAdapter(
                    api_key=mexc_api_key,
                    secret_key=mexc_secret_key,
                    base_url=base_url
                )
                self.logger.info("✅ MEXC broker initialized")
            else:
                self.logger.warning("⚠️ MEXC broker not configured (missing API keys)")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize MEXC broker: {e}")

        # Initialize Phemex
        try:
            phemex_api_key = os.getenv('PHEMEX_API_KEY')
            phemex_secret_key = os.getenv('PHEMEX_SECRET_KEY')
            phemex_testnet = os.getenv('PHEMEX_TESTNET', 'true').lower() == 'true'

            if phemex_api_key and phemex_secret_key:
                # Use testnet URL if testnet is enabled
                base_url = "https://testnet-api.phemex.com" if phemex_testnet else "https://api.phemex.com"
                self.brokers['phemex'] = PhemexBrokerAdapter(
                    api_key=phemex_api_key,
                    secret_key=phemex_secret_key,
                    base_url=base_url
                )
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

        # Check for broker-specific order placement settings
        import os

        # Check if any specific broker is enabled for exclusive order placement
        bingx_order_placement_enabled = os.getenv('BINGX_ORDER_PLACEMENT_ENABLED', 'false').lower() == 'true'
        binance_order_placement_enabled = os.getenv('BINANCE_ORDER_PLACEMENT_ENABLED', 'false').lower() == 'true'
        mexc_order_placement_enabled = os.getenv('MEXC_ORDER_PLACEMENT_ENABLED', 'false').lower() == 'true'
        phemex_order_placement_enabled = os.getenv('PHEMEX_ORDER_PLACEMENT_ENABLED', 'false').lower() == 'true'

        # Determine which broker to use based on environment variables
        # Priority: Check each broker in order, first one enabled gets priority
        best_exchange = None
        if bingx_order_placement_enabled and 'bingx' in self.brokers:
            best_exchange = 'bingx'
            self.logger.info(f"🎯 BINGX ORDER PLACEMENT ENABLED - EXECUTING ORDER ON BINGX: {order}")
        elif binance_order_placement_enabled and 'binance' in self.brokers:
            best_exchange = 'binance'
            self.logger.info(f"🎯 BINANCE ORDER PLACEMENT ENABLED - EXECUTING ORDER ON BINANCE: {order}")
        elif mexc_order_placement_enabled and 'mexc' in self.brokers:
            best_exchange = 'mexc'
            self.logger.info(f"🎯 MEXC ORDER PLACEMENT ENABLED - EXECUTING ORDER ON MEXC: {order}")
        elif phemex_order_placement_enabled and 'phemex' in self.brokers:
            best_exchange = 'phemex'
            self.logger.info(f"🎯 PHEMEX ORDER PLACEMENT ENABLED - EXECUTING ORDER ON PHEMEX: {order}")
        else:
            # Find the best exchange for this symbol (original behavior)
            best_exchange = self._find_best_exchange_for_symbol(symbol_str)

        if best_exchange and best_exchange in self.brokers:
            broker = self.brokers[best_exchange]

            # Enhance order with risk parameters if they're missing
            # This ensures institutional standards are met even if the Strategy layer didn't add them
            order = self._enhance_order_with_risk_parameters(order)

            # Validate the order against risk management standards
            is_valid = self._validate_order_risk(order)
            if not is_valid:
                self.logger.error(f"❌ ORDER REJECTED: Risk validation failed for order: {order}")
                raise ValueError(f"Order failed risk validation: {order}")

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

    def _enhance_order_with_risk_parameters(self, order: Order) -> Order:
        """Enhance order with risk parameters if they're missing."""
        # Check if the order already has SL/TP parameters
        has_stop_loss = hasattr(order, 'stop_loss_price') and order.stop_loss_price is not None
        has_take_profit = hasattr(order, 'take_profit_price') and order.take_profit_price is not None

        # If both SL and TP are already present, return the order as is
        if has_stop_loss and has_take_profit:
            return order

        # If SL/TP are missing, we need to add them
        # This should ideally be done by the Strategy layer, but we'll add defaults here
        # to ensure institutional standards are met
        if order.price is not None and order.price.amount is not None:
            current_price = float(order.price.amount)

            # Calculate default SL/TP values based on risk management principles
            sl_multiplier = 0.02  # 2% stop loss
            tp_multiplier = 0.03  # 3% take profit (1:1.5 risk/reward ratio)

            # Calculate SL and TP prices based on order side
            if hasattr(order, 'side') and order.side.name == 'BUY':
                # For BUY orders: SL below entry, TP above entry
                sl_price = current_price * (1 - sl_multiplier)
                tp_price = current_price * (1 + tp_multiplier)
            else:  # SELL
                # For SELL orders: SL above entry, TP below entry
                sl_price = current_price * (1 + sl_multiplier)  # SL above for SELL (stop loss if price rises)
                tp_price = current_price * (1 - tp_multiplier)  # TP below for SELL (take profit when price falls)

            # Create enhanced order with SL/TP if they were missing
            from domain.entities.trading_entities import Order as DomainOrder
            from domain.value_objects import Money
            from datetime import datetime

            # Create a new order with the missing risk parameters
            enhanced_order = DomainOrder(
                symbol=getattr(order, 'symbol', 'UNKNOWN'),
                side=getattr(order, 'side', None),
                order_type=getattr(order, 'order_type', 'MARKET'),
                quantity=getattr(order, 'quantity', 1.0),
                price=getattr(order, 'price', None),
                strategy_name=getattr(order, 'strategy_name', 'default'),
                timestamp=getattr(order, 'timestamp', datetime.now()),
                position_side=getattr(order, 'position_side', 'BOTH'),
                stop_loss_price=Money(amount=sl_price, currency='USDT') if not has_stop_loss else getattr(order, 'stop_loss_price', None),
                take_profit_price=Money(amount=tp_price, currency='USDT') if not has_take_profit else getattr(order, 'take_profit_price', None),
                stop_price=getattr(order, 'stop_price', None),
                time_in_force=getattr(order, 'time_in_force', 'GTC'),
                client_order_id=getattr(order, 'client_order_id', None),
                parent_signal=getattr(order, 'parent_signal', None),
                risk_adjusted_quantity=getattr(order, 'risk_adjusted_quantity', None)
            )

            self.logger.warning(f"⚠️ Order enhanced with default SL/TP: SL={sl_price}, TP={tp_price}. "
                              f"This should ideally be handled by the Strategy layer.")

            return enhanced_order
        else:
            # If we don't have a price to calculate SL/TP, we can't enhance the order
            # In this case, we'll log a warning but still proceed (though this is not ideal)
            self.logger.warning(f"⚠️ Cannot enhance order with SL/TP: no price available: {order}")
            return order

    def _validate_order_risk(self, order: Order) -> bool:
        """Validate order against risk management standards."""
        # Import the risk management service to validate the order
        try:
            from infrastructure.risk.advanced_risk_management import AdvancedRiskManagementService

            # Create a temporary risk management instance for validation
            # In a proper architecture, this would be injected as a dependency
            risk_service = AdvancedRiskManagementService()

            # Validate the order against risk parameters
            is_valid = risk_service.validate_order_risk(order)

            if not is_valid:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.warning(f"Order failed risk validation: {risk_service.violations}")

            return is_valid
        except ImportError:
            # If risk management service is not available, log warning but allow order to proceed
            if hasattr(self, 'logger') and self.logger:
                self.logger.warning("Risk management service not available for validation")
            return True  # Allow order to proceed if risk service unavailable
        except Exception as e:
            if hasattr(self, 'logger') and self.logger:
                self.logger.warning(f"Risk validation error: {e}, allowing order to proceed")
            return True  # Allow order to proceed if validation fails

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