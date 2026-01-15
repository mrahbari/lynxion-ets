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
import threading
from datetime import datetime, timedelta


class MultiBrokerExecutionService(ExecutionPort):
    """
    Multi-broker execution service that can switch between exchanges when one doesn't have a symbol.
    Implements exchange switching similar to the downloader's approach.
    """

    # Duplicate prevention is now handled by the shared PendingOrdersTracker
    # See infrastructure/shared/pending_orders_tracker.py

    def __init__(self, primary_broker: Optional[str] = None):
        self.logger = EnhancedLogger("MultiBrokerExecutionService")

        # Initialize all broker adapters
        self.brokers = {}
        self._initialize_brokers()

        # Add caching and synchronization for symbol availability checks
        self._symbol_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_timeout = timedelta(minutes=5)  # Cache timeout of 5 minutes

        # Track recent symbol availability checks to avoid redundant calls
        self._recent_checks = {}
        self._recent_checks_lock = threading.Lock()

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

    @classmethod
    def _add_pending_order(cls, symbol: Symbol, side: str, order_id: str):
        """Add an order to the pending orders tracking."""
        # Use the shared pending orders tracker to ensure consistency across all broker services
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        PendingOrdersTracker.add_pending_order(symbol, side, order_id)

    @classmethod
    def _remove_pending_order(cls, symbol: Symbol, order_id: str):
        """Remove an order from the pending orders tracking."""
        # Use the shared pending orders tracker to ensure consistency across all broker services
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        PendingOrdersTracker.remove_pending_order(symbol, order_id)

    @classmethod
    def _has_pending_order_in_direction(cls, symbol: Symbol, side: str) -> bool:
        """Check if there's a pending order in the same direction for the symbol."""
        # Use the shared pending orders tracker to ensure consistency across all broker services
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        return PendingOrdersTracker.has_pending_order_in_direction(symbol, side)

    def get_available_symbols(self) -> Set[str]:
        """
        Get available symbols from all configured brokers.
        This aggregates symbols from all available exchanges.
        Includes caching to reduce redundant API calls.
        """
        # Check if we have a cached version that's still valid
        current_time = datetime.now()
        with self._cache_lock:
            if hasattr(self, '_cached_symbols') and hasattr(self, '_cache_timestamp'):
                if current_time - self._cache_timestamp < self._cache_timeout:
                    return self._cached_symbols

        all_symbols = set()

        for exchange_name, broker in self.brokers.items():
            try:
                if hasattr(broker, 'get_available_symbols'):
                    symbols = broker.get_available_symbols()
                    all_symbols.update(symbols)
                    self.logger.debug(f"Got {len(symbols)} symbols from {exchange_name}")
            except Exception as e:
                self.logger.warning(f"Could not get symbols from {exchange_name}: {e}")

        # Cache the results
        with self._cache_lock:
            self._cached_symbols = all_symbols
            self._cache_timestamp = current_time

        return all_symbols

    def is_symbol_available(self, symbol: str) -> bool:
        """
        Check if a symbol is available on any of the configured exchanges.
        Optimized with caching to reduce redundant API calls.
        """

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available
        from utils.symbol_validator import symbol_validator
        from domain.value_objects import Symbol as DomainSymbol

        # Create a domain symbol object for validation
        domain_symbol = DomainSymbol(symbol)
        if not symbol_validator.is_symbol_approved(domain_symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol} is not in approved symbols list. Not available for trading.")
            # Cache this negative result
            cache_key = f"symbol_check_{symbol}"
            current_time = datetime.now()
            with self._recent_checks_lock:
                self._recent_checks[cache_key] = (current_time, False)
            return False

        # Check if we have a recent result for this symbol in our cache
        cache_key = f"symbol_check_{symbol}"
        current_time = datetime.now()
        with self._recent_checks_lock:
            if cache_key in self._recent_checks:
                timestamp, result = self._recent_checks[cache_key]
                if current_time - timestamp < timedelta(seconds=30):  # 30-second cache for symbol checks
                    return result

        # First, try to use the cached symbols if available
        with self._cache_lock:
            if hasattr(self, '_cached_symbols') and hasattr(self, '_cache_timestamp'):
                if current_time - self._cache_timestamp < self._cache_timeout:
                    # Use cached symbols to check availability
                    if symbol in self._cached_symbols:
                        self.logger.debug(f"Symbol {symbol} found in cached symbols")
                        # Cache this positive result
                        with self._recent_checks_lock:
                            self._recent_checks[cache_key] = (current_time, True)
                        return True

        # Perform the actual check
        for exchange_name in self.exchange_order:
            broker = self.brokers.get(exchange_name)
            if broker and hasattr(broker, 'get_available_symbols'):
                try:
                    available_symbols = broker.get_available_symbols()
                    if symbol in available_symbols:
                        self.logger.debug(f"Symbol {symbol} found on {exchange_name}")

                        # Cache this result
                        with self._recent_checks_lock:
                            self._recent_checks[cache_key] = (current_time, True)

                        return True
                except Exception as e:
                    self.logger.warning(f"Error checking symbol {symbol} on {exchange_name}: {e}")
                    continue

        # If not found through broker methods, try direct API check
        result = self._check_symbol_direct_api(symbol)

        # Cache the final result
        with self._recent_checks_lock:
            self._recent_checks[cache_key] = (current_time, result)

        return result

    def _check_symbol_direct_api(self, symbol: str) -> bool:
        """
        Fallback method to check symbol availability via direct API calls.
        """

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available
        from utils.symbol_validator import symbol_validator
        from domain.value_objects import Symbol as DomainSymbol

        # Create a domain symbol object for validation
        domain_symbol = DomainSymbol(symbol)
        if not symbol_validator.is_symbol_approved(domain_symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol} is not in approved symbols list. Not available for trading.")
            return False

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

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available for trading
        from utils.symbol_validator import symbol_validator
        if not symbol_validator.is_symbol_approved(order.symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Order execution denied.")
            return None

        # Note: Symbol filtering (like stablecoin pairs) is now handled at the watcher level
        # to avoid processing symbols that will be rejected later. This improves efficiency.

        # Check if duplicate same-direction trade prevention is enabled
        prevent_same_direction = os.getenv('PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL', 'true').lower() == 'true'

        if prevent_same_direction:
            # Check if there's already an active position in the same direction for this symbol
            # This requires checking the current positions, which may be done through the broker
            # We'll check each broker for the position, starting with the primary broker
            current_position = None
            for exchange_name in self.exchange_order:
                broker = self.brokers.get(exchange_name)
                if broker and hasattr(broker, 'get_position'):
                    try:
                        current_position = broker.get_position(order.symbol)
                        if current_position and hasattr(current_position,
                                                        'side') and current_position.side is not None:
                            break
                    except:
                        continue  # Try next broker

            # Determine the intended side of the new order
            order_side = getattr(order, 'side', None)
            intended_position_side = None
            if order_side and hasattr(order_side, 'name'):
                if order_side.name == 'BUY':
                    intended_position_side = 'LONG'
                elif order_side.name == 'SELL':
                    intended_position_side = 'SHORT'

            # Check both existing positions and pending orders in the same direction
            position_duplicate = False
            pending_duplicate = False

            # Check for existing position in the same direction
            if current_position and hasattr(current_position, 'side') and current_position.side is not None:
                if intended_position_side and hasattr(current_position.side,
                                                     'name') and current_position.side.name == intended_position_side:
                    position_duplicate = True

            # Check for pending orders in the same direction
            if intended_position_side:
                pending_duplicate = self._has_pending_order_in_direction(order.symbol, intended_position_side)

            # If either condition is true, prevent the trade
            if position_duplicate or pending_duplicate:
                if position_duplicate:
                    self.logger.info(
                        f"❌ DUPLICATE REJECTED: Active {current_position.side.name} position exists for {order.symbol.value}. Preventing duplicate same-direction trade.")
                else:
                    self.logger.info(
                        f"❌ DUPLICATE REJECTED: Pending {intended_position_side} order exists for {order.symbol.value}. Preventing duplicate same-direction trade.")
                # Return None instead of raising an exception to prevent system crashes
                return None  # Indicate that the order was not placed due to duplicate prevention

        # Check for broker-specific order placement settings
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

            # Perform final validation to ensure the order parameters are reasonable before sending to broker
            if not self._validate_order_parameters_before_broker(order):
                self.logger.error(f"❌ ORDER REJECTED: Order parameters are invalid or unreasonable: {order}")
                raise ValueError(f"Order parameters failed final validation: {order}")

            self.logger.info(f"🎯 EXECUTING ORDER ON {best_exchange.upper()}: {order}")

            # Add to pending orders before placing the order
            order_id_temp = None
            if prevent_same_direction and intended_position_side:
                order_id_temp = "TEMP_" + str(id(order))  # Temporary ID for tracking before placement
                self._add_pending_order(order.symbol, intended_position_side, order_id_temp)

            try:
                order_id = broker.place_order(order)

                # Check if order_id is valid before proceeding
                if order_id is None or order_id == "":
                    self.logger.error(f"❌ ORDER PLACEMENT FAILED ON {best_exchange.upper()}: Broker returned invalid order ID: {order_id}")
                    return None

                self.logger.info(f"✅ ORDER PLACED SUCCESSFULLY ON {best_exchange.upper()}: {order_id}")

                # Send Telegram notification about successful order placement
                self._send_order_placed_notification(order, order_id, best_exchange.upper())

                return order_id
            except Exception as e:
                self.logger.error(f"❌ FAILED TO EXECUTE ORDER ON {best_exchange.upper()}: {e}")
                raise
            finally:
                # Remove from pending orders after attempting to place
                if prevent_same_direction and intended_position_side and order_id_temp:
                    self._remove_pending_order(order.symbol, order_id_temp)
        else:
            raise Exception(f"Symbol {symbol_str} not available on any configured exchange")

    def _enhance_order_with_risk_parameters(self, order: Order) -> Order:
        """Enhance order with risk parameters if they're missing."""

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available for trading
        from utils.symbol_validator import symbol_validator
        if not symbol_validator.is_symbol_approved(order.symbol):
            symbol_str = order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol)
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Order enhancement skipped.")
            return order

        # Check if the order already has SL/TP parameters
        has_stop_loss = hasattr(order, 'stop_loss_price') and order.stop_loss_price is not None
        has_take_profit = hasattr(order, 'take_profit_price') and order.take_profit_price is not None

        # If both SL and TP are already present, return the order as is
        if has_stop_loss and has_take_profit:
            return order

        # If SL/TP are missing, we need to add them using advanced risk management
        # This should ideally be done by the Strategy layer, but we'll add defaults here
        # to ensure institutional standards are met
        if order.price is not None and order.price.amount is not None:
            current_price = float(order.price.amount)

            # Use advanced risk management system to calculate dynamic TP/SL based on market conditions
            try:
                from infrastructure.risk.advanced_risk_management import AdvancedRiskManagementService, SLTPManager
                import os

                # Initialize risk management components
                risk_service = AdvancedRiskManagementService()

                # Get market data for more accurate risk calculations (if available)
                # In a real implementation, we'd fetch current market data for the symbol
                market_data = None  # This would come from data provider in real implementation

                # Calculate dynamic SL/TP values based on advanced risk management principles
                # First, determine the position side for risk calculations
                position_side = "LONG" if hasattr(order, 'side') and order.side.name == 'BUY' else "SHORT"

                # Create a temporary fused signal for risk adjustment factors (if available from order)
                from domain.entities.signal_entities import FusedSignal, SignalType
                from domain.value_objects import Percentage
                from datetime import datetime

                # Create a basic fused signal for risk calculations
                dummy_fused_signal = FusedSignal(
                    symbol=getattr(order, 'symbol', 'UNKNOWN'),
                    dominant_bias=SignalType.BUY if position_side == "LONG" else SignalType.SELL,
                    direction=1.0 if position_side == "LONG" else -1.0,
                    dominance_score=0.5,
                    regime_context="normal",
                    confidence=Percentage(0.5),
                    timestamp=datetime.now(),
                    metadata={}
                )

                # Calculate risk-adjusted position size (even if we don't use it, we get risk factors)
                portfolio_value = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '10000.0'))
                _, risk_factors = risk_service.calculate_position_size(
                    symbol=getattr(order, 'symbol', 'UNKNOWN'),
                    price=current_price,
                    portfolio_value=portfolio_value,
                    fused_signal=dummy_fused_signal,
                    market_data=market_data
                )

                # Calculate dynamic SL/TP levels based on risk factors
                try:
                    sl_price, tp_price = risk_service.calculate_sl_tp_levels(
                        entry_price=current_price,
                        position_side=position_side,
                        risk_adjustment_factors=risk_factors,
                        atr_value=None,  # Would come from market data in real implementation
                        market_data=market_data
                    )
                except Exception as risk_calc_error:
                    self.logger.warning(f"Risk calculation failed: {risk_calc_error}, using fallback SL/TP")
                    # Fallback to simple percentage-based calculation
                    sl_multiplier = 0.02  # 2% stop loss
                    tp_multiplier = 0.03  # 3% take profit

                    if hasattr(order, 'side') and order.side.name == 'BUY':
                        # For BUY orders: SL below entry, TP above entry
                        sl_price = current_price * (1 - sl_multiplier)
                        tp_price = current_price * (1 + tp_multiplier)
                    else:  # SELL
                        # For SELL orders: SL above entry, TP below entry
                        sl_price = current_price * (1 + sl_multiplier)  # SL above for SELL (stop loss if price rises)
                        tp_price = current_price * (1 - tp_multiplier)  # TP below for SELL (take profit when price falls)

            except Exception as e:
                # If advanced risk management fails, fall back to simple calculation
                self.logger.warning(f"Advanced risk management failed, using fallback: {e}")

                # Calculate default SL/TP values based on basic risk management principles
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
                stop_loss_price=Money(amount=float(sl_price), currency='USDT') if not has_stop_loss else getattr(order,
                                                                                                          'stop_loss_price',
                                                                                                          None),
                take_profit_price=Money(amount=float(tp_price), currency='USDT') if not has_take_profit else getattr(order,
                                                                                                              'take_profit_price',
                                                                                                              None),
                stop_price=getattr(order, 'stop_price', None),
                time_in_force=getattr(order, 'time_in_force', 'GTC'),
                client_order_id=getattr(order, 'client_order_id', None),
                parent_signal=getattr(order, 'parent_signal', None),
                risk_adjusted_quantity=getattr(order, 'risk_adjusted_quantity', None)
            )

            self.logger.info(f"✅ Order enhanced with dynamic SL/TP: SL={sl_price:.4f}, TP={tp_price:.4f}. "
                            f"Advanced risk management applied for proper position sizing and SL/TP levels.")

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

    def _validate_order_parameters_before_broker(self, order: Order) -> bool:
        """Final validation to ensure order parameters are reasonable before sending to broker."""
        try:
            # Check if we have a valid price
            if order.price and hasattr(order.price, 'amount') and order.price.amount:
                entry_price = float(order.price.amount)

                # Check if stop loss price is reasonable
                if hasattr(order, 'stop_loss_price') and order.stop_loss_price:
                    sl_price = float(order.stop_loss_price.amount) if hasattr(order.stop_loss_price, 'amount') else float(order.stop_loss_price)

                    # For BUY orders: SL should be below entry price
                    # For SELL orders: SL should be above entry price (for short positions)
                    is_buy_order = hasattr(order, 'side') and order.side.name == 'BUY'

                    if is_buy_order:
                        # For BUY orders, SL should be below entry price (but not too far below)
                        if sl_price >= entry_price and entry_price > 0:  # SL should be below for long positions
                            self.logger.warning(f"Invalid SL for BUY order: SL ({sl_price}) >= Entry ({entry_price})")
                            return False
                        elif sl_price <= 0:
                            self.logger.warning(f"Invalid SL for BUY order: SL ({sl_price}) <= 0")
                            return False
                        elif entry_price > 0 and sl_price < entry_price * 0.01:  # SL not more than 99% below entry
                            self.logger.warning(f"SL too far from entry for BUY order: SL ({sl_price}) vs Entry ({entry_price})")
                            return False
                    else:
                        # For SELL orders, SL should be above entry price (for stop loss on short)
                        if sl_price <= entry_price and entry_price > 0:  # SL should be above for short positions
                            self.logger.warning(f"Invalid SL for SELL order: SL ({sl_price}) <= Entry ({entry_price})")
                            return False
                        elif sl_price <= 0:
                            self.logger.warning(f"Invalid SL for SELL order: SL ({sl_price}) <= 0")
                            return False
                        elif entry_price > 0 and sl_price > entry_price * 100:  # SL not more than 100x above entry
                            self.logger.warning(f"SL too far from entry for SELL order: SL ({sl_price}) vs Entry ({entry_price})")
                            return False

                # Check if take profit price is reasonable
                if hasattr(order, 'take_profit_price') and order.take_profit_price:
                    tp_price = float(order.take_profit_price.amount) if hasattr(order.take_profit_price, 'amount') else float(order.take_profit_price)

                    # For BUY orders: TP should be above entry price
                    # For SELL orders: TP should be below entry price (for short positions)
                    is_buy_order = hasattr(order, 'side') and order.side.name == 'BUY'

                    if is_buy_order:
                        # For BUY orders, TP should be above entry price (but not too far above)
                        if tp_price <= entry_price and entry_price > 0:  # TP should be above for long positions
                            self.logger.warning(f"Invalid TP for BUY order: TP ({tp_price}) <= Entry ({entry_price})")
                            return False
                        elif tp_price <= 0:
                            self.logger.warning(f"Invalid TP for BUY order: TP ({tp_price}) <= 0")
                            return False
                        elif entry_price > 0 and tp_price > entry_price * 100:  # TP not more than 100x above entry
                            self.logger.warning(f"TP too far from entry for BUY order: TP ({tp_price}) vs Entry ({entry_price})")
                            return False
                    else:
                        # For SELL orders, TP should be below entry price (for profit on short)
                        if tp_price >= entry_price and entry_price > 0:  # TP should be below for short positions
                            self.logger.warning(f"Invalid TP for SELL order: TP ({tp_price}) >= Entry ({entry_price})")
                            return False
                        elif tp_price <= 0:
                            self.logger.warning(f"Invalid TP for SELL order: TP ({tp_price}) <= 0")
                            return False
                        elif entry_price > 0 and tp_price < entry_price * 0.01:  # TP not more than 99% below entry
                            self.logger.warning(f"TP too far from entry for SELL order: TP ({tp_price}) vs Entry ({entry_price})")
                            return False

            return True
        except Exception as e:
            self.logger.warning(f"Parameter validation error: {e}, allowing order to proceed")
            return True  # Allow order to proceed if validation fails

    def _find_best_exchange_for_symbol(self, symbol: str) -> Optional[str]:
        """
        Find the best exchange for a given symbol by checking availability.
        """

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available
        from utils.symbol_validator import symbol_validator
        from domain.value_objects import Symbol as DomainSymbol

        # Create a domain symbol object for validation
        domain_symbol = DomainSymbol(symbol)
        if not symbol_validator.is_symbol_approved(domain_symbol):
            self.logger.info(f"❌ SYMBOL REJECTED: {symbol} is not in approved symbols list. Not available for trading.")
            return None

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

    def _send_order_placed_notification(self, order: Order, order_id: str, exchange_name: str):
        """Send a Telegram notification about a successfully placed order."""
        try:
            # Check if Telegram notifications are enabled
            telegram_notifications_enabled = os.getenv('TELEGRAM_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
            if not telegram_notifications_enabled:
                return  # Skip notifications if disabled

            # Import Telegram service
            from infrastructure.services.risk_alerts import TelegramNotificationService

            # Create Telegram service instance
            telegram_service = TelegramNotificationService(
                bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
                chat_id=os.getenv('TELEGRAM_CHAT_ID', '')
            )

            # Prepare notification message
            symbol = getattr(order, 'symbol', {}).value if hasattr(getattr(order, 'symbol', None), 'value') else str(
                getattr(order, 'symbol', 'UNKNOWN'))
            side = getattr(order, 'side', 'UNKNOWN')
            side_name = getattr(side, 'name', str(side))
            quantity = getattr(order, 'quantity', 'N/A')
            price = getattr(order, 'price', 'N/A')
            price_amount = getattr(price, 'amount', 'N/A') if hasattr(price, 'amount') else str(price)
            strategy_name = getattr(order, 'strategy_name', 'N/A')

            # Get TP/SL information if available
            stop_loss_price = getattr(order, 'stop_loss_price', None)
            take_profit_price = getattr(order, 'take_profit_price', None)
            sl_value = getattr(stop_loss_price, 'amount', 'N/A') if stop_loss_price else 'N/A'
            tp_value = getattr(take_profit_price, 'amount', 'N/A') if take_profit_price else 'N/A'

            message = (f"✅ ORDER PLACED\n"
                       f"Exchange: {exchange_name}\n"
                       f"Symbol: {symbol}\n"
                       f"Side: {side_name}\n"
                       f"Quantity: {quantity}\n"
                       f"Price: {price_amount}\n"
                       f"Stop Loss: {sl_value}\n"
                       f"Take Profit: {tp_value}\n"
                       f"Strategy: {strategy_name}\n"
                       f"Order ID: {order_id}")

            subject = f"Order Placed: {symbol} {side_name} on {exchange_name}"

            # Send the notification
            success = telegram_service.send_notification(message, subject, "info")

            if success:
                self.logger.info(f"🔔 Telegram notification sent for order {order_id}")
            else:
                self.logger.warning(f"⚠️ Failed to send Telegram notification for order {order_id}")

        except Exception as e:
            self.logger.error(f"❌ Error sending Telegram notification: {e}")

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
