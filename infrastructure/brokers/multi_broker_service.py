"""
Multi-Broker Service for handling exchange switching and symbol availability checks.
This service provides exchange switching capabilities similar to the downloader's approach.
"""
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional, Set

from domain.entities import Order
from domain.ports.execution_ports import ExecutionPort
from domain.value_objects import Symbol
from infrastructure.brokers.broker_adapters import (
    BingXBrokerAdapter, BinanceBrokerAdapter, MEXCBrokerAdapter, PhemexBrokerAdapter
)
from infrastructure.brokers.symbol_format_helper import SymbolFormatHelper
from shared.logger import EnhancedLogger


class MultiBrokerExecutionService(ExecutionPort):
    """
    Multi-broker execution service that can switch between exchanges when one doesn't have a symbol.
    Implements exchange switching similar to the downloader's approach.
    """

    # Duplicate prevention is now handled by the shared PendingOrdersTracker
    # See infrastructure/shared/pending_orders_tracker.py

    def __init__(self, settings, primary_broker: Optional[str] = None):
        # Settings injected by the composition root (E1.T4); same values as before,
        # without importing bootstrap.settings.loaders here.
        self._settings = settings
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
            self.primary_broker = self._settings.broker.default_broker.lower()  # Default to bingx as requested

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

        # B5: map each placed order_id -> (exchange, symbol) so cancel/status can route to
        # the originating adapter (the layer previously had no such mapping).
        self._order_exchange_map = {}
        self._order_map_lock = threading.Lock()

        # B3 startup recovery: rebuild the order->exchange map and surface in-flight orders
        # from the durable live order journal, so cancel/status survive a restart and
        # in-flight orders can be reconciled against the broker.
        try:
            from infrastructure.execution.live_order_journal import live_order_journal
            rec = live_order_journal.recover()
            self._order_exchange_map.update(rec.get("order_exchange_map", {}))
            in_flight = rec.get("in_flight", [])
            if in_flight:
                self.logger.warning(
                    f"♻️ STARTUP RECOVERY: {len(in_flight)} in-flight order(s) from journal "
                    f"need broker reconciliation: {[o.get('order_id') or o.get('order_ref') for o in in_flight]}")
            elif rec.get("total_orders"):
                self.logger.info(
                    f"♻️ STARTUP RECOVERY: loaded {rec['total_orders']} journaled order(s); none in-flight")
        except Exception as e:
            self.logger.warning(f"Startup recovery from live order journal skipped: {e}")

    def _initialize_brokers(self):
        """Initialize all available broker adapters."""
        # Initialize Binance
        try:
            binance_config = {
                'api_key': self._settings.broker.binance_api_key if self._settings.broker and self._settings.broker.binance_api_key else '',
                'secret_key': self._settings.broker.binance_secret_key if self._settings.broker and self._settings.broker.binance_secret_key else '',
                'testnet': self._settings.broker.binance_testnet if self._settings.broker and hasattr(self._settings.broker,
                                                                                        'binance_testnet') else True
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
                'api_key': self._settings.broker.bingx_api_key if self._settings.broker and self._settings.broker.bingx_api_key else '',
                'secret_key': self._settings.broker.bingx_secret_key if self._settings.broker and self._settings.broker.bingx_secret_key else '',
                'passphrase': self._settings.broker.bingx_passphrase if self._settings.broker and self._settings.broker.bingx_passphrase else '',
                'testnet': self._settings.broker.bingx_testnet if self._settings.broker and hasattr(self._settings.broker,
                                                                                      'bingx_testnet') else True
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
            mexc_api_key = self._settings.broker.mexc_api_key if self._settings.broker and self._settings.broker.mexc_api_key else ''
            mexc_secret_key = self._settings.broker.mexc_secret_key if self._settings.broker and self._settings.broker.mexc_secret_key else ''
            mexc_testnet = self._settings.broker.mexc_testnet if self._settings.broker and hasattr(self._settings.broker,
                                                                                     'mexc_testnet') else True

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
            phemex_api_key = self._settings.broker.phemex_api_key if self._settings.broker and self._settings.broker.phemex_api_key else ''
            phemex_secret_key = self._settings.broker.phemex_secret_key if self._settings.broker and self._settings.broker.phemex_secret_key else ''
            phemex_testnet = self._settings.broker.phemex_testnet if self._settings.broker and hasattr(self._settings.broker,
                                                                                         'phemex_testnet') else True

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

    @classmethod
    def _has_any_pending_order(cls, symbol: Symbol) -> bool:
        """Check if there's any pending order for the symbol."""
        # Use the shared pending orders tracker to ensure consistency across all broker services
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        return len(PendingOrdersTracker.get_pending_orders_for_symbol(symbol)) > 0

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
        from infrastructure.services.symbol_validator import symbol_validator
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
        from infrastructure.services.symbol_validator import symbol_validator
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
                    api_url = f"https://open-api.bingx.com/openApi/quote/v1/ticker/price?symbol={SymbolFormatHelper.format_symbol_for_exchange(symbol, exchange_name)}"
                elif exchange_name == 'mexc':
                    api_url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
                elif exchange_name == 'phemex':
                    api_url = f"https://api.phemex.com/md/ticker/24hr?symbol={symbol}"
                else:
                    continue  # Skip unknown exchanges

                # Use session with proper connection management
                with requests.Session() as session:
                    response = session.get(api_url, timeout=5)
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
        from infrastructure.services.symbol_validator import symbol_validator
        if not symbol_validator.is_symbol_approved(order.symbol):
            self.logger.info(
                f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Order execution denied.")
            return None

        # Note: Symbol filtering (like stablecoin pairs) is now handled at the watcher level
        # to avoid processing symbols that will be rejected later. This improves efficiency.

        # Check if duplicate same-direction trade prevention is enabled
        prevent_same_direction = self._settings.execution.prevent_same_direction_trade_per_symbol if self._settings.execution and hasattr(
            self._settings.execution, 'prevent_same_direction_trade_per_symbol') else True

        if prevent_same_direction:
            order_side = getattr(order, 'side', None)
            intended_position_side = None
            if order_side:
                order_side_str = order_side.name if hasattr(order_side, 'name') else (order_side.value if hasattr(order_side, 'value') else str(order_side))
                if order_side_str.upper() in ('BUY', 'LONG'):
                    intended_position_side = 'LONG'
                elif order_side_str.upper() in ('SELL', 'SHORT'):
                    intended_position_side = 'SHORT'

            # Check for any pending orders on the symbol using the shared tracker
            pending_duplicate = self._has_any_pending_order(order.symbol)

            # If there's a pending order, prevent the trade
            if pending_duplicate:
                self.logger.info(
                    f"⚠️ CONFLICT CHECK BLOCKED: Internal pending order exists on {order.symbol.value} — broker confirmation needed.")
                # Return None instead of raising an exception to prevent system crashes
                return None  # Indicate that the order was not placed due to duplicate prevention

        # Check for broker-specific order placement settings
        # Check if any specific broker is enabled for exclusive order placement
        bingx_order_placement_enabled = self._settings.broker.bingx_order_placement_enabled if self._settings.broker and hasattr(
            self._settings.broker, 'bingx_order_placement_enabled') else False
        binance_order_placement_enabled = self._settings.broker.binance_order_placement_enabled if self._settings.broker and hasattr(
            self._settings.broker, 'binance_order_placement_enabled') else False
        mexc_order_placement_enabled = self._settings.broker.mexc_order_placement_enabled if self._settings.broker and hasattr(
            self._settings.broker, 'mexc_order_placement_enabled') else False
        phemex_order_placement_enabled = self._settings.broker.phemex_order_placement_enabled if self._settings.broker and hasattr(
            self._settings.broker, 'phemex_order_placement_enabled') else False

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
                return None  # Return None instead of raising to prevent system crashes

            # Perform final validation to ensure the order parameters are reasonable before sending to broker
            if not self._validate_order_parameters_before_broker(order):
                self.logger.error(f"❌ ORDER REJECTED: Order parameters are invalid or unreasonable: {order}")
                # Return None instead of raising an exception to prevent system crashes
                return None

            self.logger.info(f"🎯 EXECUTING ORDER ON {best_exchange.upper()}: {order}")

            journal_ref = None
            try:
                from shared.live_execution_guard import live_execution_guard
                # Only a real (LIVE/TESTNET) send needs a connected broker. PAPER orders are
                # filled by the paper-trading engine and must NOT be gated by connectivity
                # (Phase-10 found paper orders were dropped here before reaching the guard).
                if live_execution_guard.evaluate(best_exchange, self._settings, order).is_real_send:
                    if hasattr(broker, 'connected'):
                        if not broker.connected:
                            self.logger.error(f"❌ BROKER NOT CONNECTED: Cannot place order on {best_exchange.upper()}")
                            return None
                    elif hasattr(broker, 'connect') and callable(getattr(broker, 'connect')):
                        # Try to connect if not connected
                        try:
                            if not getattr(broker, 'connected', False):
                                broker.connect()
                        except Exception as conn_error:
                            self.logger.error(f"❌ FAILED TO CONNECT TO BROKER {best_exchange.upper()}: {conn_error}")
                            return None

                    # B3: write a durable INTENT record BEFORE the send (closes the lost-write
                    # window). The client_order_id is generated here so the journal and the
                    # adapter idempotency key (B2) match; a crash after send leaves a recoverable
                    # INTENT/SUBMITTED record for startup reconciliation.
                    try:
                        from infrastructure.execution.live_order_journal import live_order_journal
                        coid = getattr(order, 'client_order_id', None) or ('x' + uuid.uuid4().hex[:30])
                        try:
                            order.client_order_id = coid
                        except Exception:
                            pass
                        sym = order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol)
                        side_name = getattr(order.side, 'name', str(order.side))
                        journal_ref = live_order_journal.record_intent(
                            sym, side_name, order.quantity, best_exchange, coid)
                    except Exception:
                        journal_ref = None

                # === LIVE_EXECUTION_GUARD — single, race-free execution-safety enforcement point (Phase-9) ===
                # Atomically: evaluate -> write the Execution Truth Ledger (BEFORE any send)
                # -> send, all under the guard lock so the kill switch / circuit breaker
                # cannot interleave between decision and send. Enforces paper_trading override,
                # testnet-only-selects-endpoint, explicit LIVE_TRADING opt-in for live sends,
                # per-broker order-placement permission, kill switch and circuit breaker.
                from shared.live_execution_guard import live_execution_guard
                guard_decision, order_id = live_execution_guard.authorize_and_send(
                    broker_name=best_exchange, settings=self._settings, order=order,
                    send_fn=lambda: broker.place_order(order))
                if not guard_decision.allowed:
                    self.logger.error(
                        f"🛑 LIVE_EXECUTION_GUARD BLOCKED order on {best_exchange.upper()}: {guard_decision.reason}")
                    return None
                if guard_decision.simulate:
                    self.logger.warning(
                        f"🧪 PAPER MODE — order SIMULATED on {best_exchange.upper()} "
                        f"(NOT sent to exchange): {order_id} [{guard_decision.reason}]")
                    if prevent_same_direction and intended_position_side:
                        self._add_pending_order(order.symbol, intended_position_side, order_id)
                    return order_id
                self.logger.info(
                    f"🔐 LIVE_EXECUTION_GUARD authorized {guard_decision.mode.value.upper()} send "
                    f"on {best_exchange.upper()}: {guard_decision.reason}")
                # === end LIVE_EXECUTION_GUARD ===

                # Check if order_id is valid before proceeding
                if order_id is None or order_id == "":
                    self.logger.error(
                        f"❌ ORDER PLACEMENT FAILED ON {best_exchange.upper()}: Broker returned invalid order ID: {order_id}")
                    if journal_ref:
                        try:
                            from infrastructure.execution.live_order_journal import live_order_journal
                            live_order_journal.record_failed(journal_ref, "broker returned no order id")
                        except Exception:
                            pass
                    return None

                # B3: durable SUBMITTED record (broker accepted; carries the exchange order_id).
                if journal_ref:
                    try:
                        from infrastructure.execution.live_order_journal import live_order_journal
                        live_order_journal.record_submitted(journal_ref, order_id, best_exchange)
                    except Exception:
                        pass

                # B5: record order_id -> (exchange, symbol) for cancel/status routing.
                with self._order_map_lock:
                    self._order_exchange_map[str(order_id)] = (best_exchange, order.symbol)

                # NOW we have a valid order ID from the broker, so we can add to pending orders
                if prevent_same_direction and intended_position_side:
                    self._add_pending_order(order.symbol, intended_position_side, order_id)

                self.logger.info(f"✅ ORDER PLACED SUCCESSFULLY ON {best_exchange.upper()}: {order_id}")

                # Send Telegram notification about successful order placement
                self._send_order_placed_notification(order, order_id, best_exchange.upper())

                return order_id
            except Exception as e:
                # Send failures are recorded (ledger + circuit breaker) inside
                # authorize_and_send before the exception propagates here. Also mark the
                # journal intent FAILED so startup recovery does not treat it as in-flight.
                if journal_ref:
                    try:
                        from infrastructure.execution.live_order_journal import live_order_journal
                        live_order_journal.record_failed(journal_ref, str(e))
                    except Exception:
                        pass
                self.logger.error(f"❌ FAILED TO EXECUTE ORDER ON {best_exchange.upper()}: {e}")
                # Still return None instead of raising to prevent system crashes
                return None
        else:
            # If no exchange is available, return None instead of raising an exception
            self.logger.error(f"❌ SYMBOL {symbol_str} not available on any configured exchange")
            return None

    def _enhance_order_with_risk_parameters(self, order: Order) -> Order:
        """Enhance order with risk parameters if they're missing."""

        # First, check if the symbol is in the approved symbols list
        # This is the primary validation - if a symbol is not approved, it's not available for trading
        from infrastructure.services.symbol_validator import symbol_validator
        if not symbol_validator.is_symbol_approved(order.symbol):
            symbol_str = order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol)
            self.logger.info(
                f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Order enhancement skipped.")
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
                order_side_name = order.side.name if hasattr(order.side, 'name') else (order.side.value if hasattr(order.side, 'value') else str(order.side)) if hasattr(order, 'side') and order.side is not None else ""
                is_buy_side = order_side_name.upper() in ('BUY', 'LONG')
                position_side = "LONG" if is_buy_side else "SHORT"

                # Create a temporary fused signal for risk adjustment factors (if available from order)
                from domain.entities import FusedSignal, SignalType
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
                portfolio_value = self._settings.position_sizing.default_account_balance if self._settings.position_sizing and hasattr(
                    self._settings.position_sizing, 'default_account_balance') else 10000.0
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

                    if is_buy_side:
                        # For BUY orders: SL below entry, TP above entry
                        sl_price = current_price * (1 - sl_multiplier)
                        tp_price = current_price * (1 + tp_multiplier)
                    else:  # SELL
                        # For SELL orders: SL above entry, TP below entry
                        sl_price = current_price * (1 + sl_multiplier)  # SL above for SELL (stop loss if price rises)
                        tp_price = current_price * (
                                    1 - tp_multiplier)  # TP below for SELL (take profit when price falls)

            except Exception as e:
                # If advanced risk management fails, fall back to simple calculation
                self.logger.warning(f"Advanced risk management failed, using fallback: {e}")

                # Calculate default SL/TP values based on basic risk management principles
                sl_multiplier = 0.02  # 2% stop loss
                tp_multiplier = 0.03  # 3% take profit (1:1.5 risk/reward ratio)

                # Calculate SL and TP prices based on order side
                if is_buy_side:
                    # For BUY orders: SL below entry, TP above entry
                    sl_price = current_price * (1 - sl_multiplier)
                    tp_price = current_price * (1 + tp_multiplier)
                else:  # SELL
                    # For SELL orders: SL above entry, TP below entry
                    sl_price = current_price * (1 + sl_multiplier)  # SL above for SELL (stop loss if price rises)
                    tp_price = current_price * (1 - tp_multiplier)  # TP below for SELL (take profit when price falls)

            # Create enhanced order with SL/TP if they were missing
            from domain.entities import Order as DomainOrder
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
                take_profit_price=Money(amount=float(tp_price), currency='USDT') if not has_take_profit else getattr(
                    order,
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
                    sl_price = float(order.stop_loss_price.amount) if hasattr(order.stop_loss_price,
                                                                              'amount') else float(
                        order.stop_loss_price)

                    # For BUY orders: SL should be below entry price
                    # For SELL orders: SL should be above entry price (for short positions)
                    order_side_name = order.side.name if hasattr(order.side, 'name') else (order.side.value if hasattr(order.side, 'value') else str(order.side)) if hasattr(order, 'side') and order.side is not None else ""
                    is_buy_order = order_side_name.upper() in ('BUY', 'LONG')

                    if is_buy_order:
                        # For BUY orders, SL should be below entry price (but not too far below)
                        if sl_price >= entry_price and entry_price > 0:  # SL should be below for long positions
                            self.logger.warning(f"Invalid SL for BUY order: SL ({sl_price}) >= Entry ({entry_price})")
                            return False
                        elif sl_price <= 0:
                            self.logger.warning(f"Invalid SL for BUY order: SL ({sl_price}) <= 0")
                            return False
                        # More reasonable range check - allow SL to be up to 50% below entry
                        elif entry_price > 0 and sl_price < entry_price * 0.5:  # SL not more than 50% below entry
                            self.logger.warning(
                                f"SL too far from entry for BUY order: SL ({sl_price}) vs Entry ({entry_price})")
                            return False
                    else:
                        # For SELL orders, SL should be above entry price (for stop loss on short)
                        if sl_price <= entry_price and entry_price > 0:  # SL should be above for short positions
                            self.logger.warning(f"Invalid SL for SELL order: SL ({sl_price}) <= Entry ({entry_price})")
                            return False
                        elif sl_price <= 0:
                            self.logger.warning(f"Invalid SL for SELL order: SL ({sl_price}) <= 0")
                            return False
                        # More reasonable range check - allow SL to be up to 50% above entry
                        elif entry_price > 0 and sl_price > entry_price * 1.5:  # SL not more than 50% above entry
                            self.logger.warning(
                                f"SL too far from entry for SELL order: SL ({sl_price}) vs Entry ({entry_price})")
                            return False

                # Check if take profit price is reasonable
                if hasattr(order, 'take_profit_price') and order.take_profit_price:
                    tp_price = float(order.take_profit_price.amount) if hasattr(order.take_profit_price,
                                                                                'amount') else float(
                        order.take_profit_price)

                    # For BUY orders: TP should be above entry price
                    # For SELL orders: TP should be below entry price (for short positions)
                    order_side_name = order.side.name if hasattr(order.side, 'name') else (order.side.value if hasattr(order.side, 'value') else str(order.side)) if hasattr(order, 'side') and order.side is not None else ""
                    is_buy_order = order_side_name.upper() in ('BUY', 'LONG')

                    if is_buy_order:
                        # For BUY orders, TP should be above entry price (but not too far above)
                        if tp_price <= entry_price and entry_price > 0:  # TP should be above for long positions
                            self.logger.warning(f"Invalid TP for BUY order: TP ({tp_price}) <= Entry ({entry_price})")
                            return False
                        elif tp_price <= 0:
                            self.logger.warning(f"Invalid TP for BUY order: TP ({tp_price}) <= 0")
                            return False
                        # More reasonable range check - allow TP to be up to 200% above entry (2x)
                        elif entry_price > 0 and tp_price > entry_price * 2.0:  # TP not more than 2x above entry
                            self.logger.warning(
                                f"TP too far from entry for BUY order: TP ({tp_price}) vs Entry ({entry_price})")
                            return False
                    else:
                        # For SELL orders, TP should be below entry price (for profit on short)
                        if tp_price >= entry_price and entry_price > 0:  # TP should be below for short positions
                            self.logger.warning(f"Invalid TP for SELL order: TP ({tp_price}) >= Entry ({entry_price})")
                            return False
                        elif tp_price <= 0:
                            self.logger.warning(f"Invalid TP for SELL order: TP ({tp_price}) <= 0")
                            return False
                        # More reasonable range check - allow TP to be up to 50% below entry
                        elif entry_price > 0 and tp_price < entry_price * 0.5:  # TP not more than 50% below entry
                            self.logger.warning(
                                f"TP too far from entry for SELL order: TP ({tp_price}) vs Entry ({entry_price})")
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
        from infrastructure.services.symbol_validator import symbol_validator
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
                api_url = f"https://open-api.bingx.com/openApi/quote/v1/ticker/price?symbol={formatted_symbol}"
            elif exchange_name == 'mexc':
                api_url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
            elif exchange_name == 'phemex':
                api_url = f"https://api.phemex.com/md/ticker/24hr?symbol={symbol}"
            else:
                return False

            # Use session with proper connection management
            with requests.Session() as session:
                response = session.get(api_url, timeout=5)
                return response.status_code == 200
        except Exception:
            return False

    def _send_order_placed_notification(self, order: Order, order_id: str, exchange_name: str):
        """Send a Telegram notification about a successfully placed order."""
        try:
            # Check if Telegram notifications are enabled
            telegram_notifications_enabled = self._settings.monitoring.telegram_notifications_enabled if self._settings.monitoring and hasattr(
                self._settings.monitoring, 'telegram_notifications_enabled') else True
            if not telegram_notifications_enabled:
                return  # Skip notifications if disabled

            # Import Telegram service
            from infrastructure.services.risk_alerts import TelegramNotificationService

            # Create Telegram service instance
            telegram_service = TelegramNotificationService(
                bot_token=self._settings.monitoring.telegram_bot_token if self._settings.monitoring and self._settings.monitoring.telegram_bot_token else '',
                chat_id=self._settings.monitoring.telegram_chat_id if self._settings.monitoring and self._settings.monitoring.telegram_chat_id else ''
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
            intent = getattr(order, 'parent_execution_intent', None)
            if (strategy_name in ('N/A', 'default', '')) and intent:
                strategy_name = getattr(intent, 'strategy_name', strategy_name)

            # Get TP/SL information if available
            stop_loss_price = getattr(order, 'stop_loss_price', None)
            take_profit_price = getattr(order, 'take_profit_price', None)
            sl_value = getattr(stop_loss_price, 'amount', 'N/A') if stop_loss_price else 'N/A'
            tp_value = getattr(take_profit_price, 'amount', 'N/A') if take_profit_price else 'N/A'

            # Get real-time timestamp for live order placement alert
            from datetime import datetime
            order_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Extract confidence and score of the order
            confidence_str = "N/A"
            score_str = "N/A"
            regime_context = "N/A"
            watcher_name = getattr(order, 'watcher_name', None) or getattr(order, 'source_watcher', None) or "N/A"

            if intent:
                intent_conf = getattr(intent, 'intent_confidence', None)
                if intent_conf:
                    conf_val = getattr(intent_conf, 'value', intent_conf)
                    try:
                        confidence_str = f"{float(conf_val) * 100:.1f}%"
                    except (ValueError, TypeError):
                        confidence_str = str(conf_val)

                metadata = getattr(intent, 'metadata', {}) or {}
                risk_adj_score = metadata.get('risk_adjusted_score', None)
                perf_score = metadata.get('performance_score', None)
                regime_context = metadata.get('regime_context', 'N/A')
                if watcher_name in ("N/A", "default"):
                    watcher_name = metadata.get('watcher_name') or metadata.get('source_watcher') or metadata.get('primary_watcher') or "N/A"

                if perf_score is not None:
                    try:
                        perf_score_str = f"{float(perf_score):.3f}"
                    except (ValueError, TypeError):
                        perf_score_str = str(perf_score)

                if risk_adj_score is not None:
                    try:
                        risk_adj_score_str = f"{float(risk_adj_score):.3f}"
                    except (ValueError, TypeError):
                        risk_adj_score_str = str(risk_adj_score)

                fused_sig = getattr(intent, 'fused_signal', None)
                if fused_sig:
                    if regime_context == 'N/A':
                        regime_context = getattr(fused_sig, 'regime_context', 'N/A')
                    if watcher_name in ("N/A", "default"):
                        fused_meta = getattr(fused_sig, 'metadata', {}) or {}
                        watcher_name = fused_meta.get('watcher_name') or fused_meta.get('primary_watcher') or fused_meta.get('source_watcher') or getattr(fused_sig, 'source_watcher', 'N/A')
                    if risk_adj_score_str == "N/A":
                        dom_score = getattr(fused_sig, 'dominance_score', None)
                        if dom_score is not None:
                            try:
                                risk_adj_score_str = f"{float(dom_score):.3f} (Dominance)"
                            except (ValueError, TypeError):
                                pass

            # Fallback watcher resolution from strategy_name if watcher is still N/A or default
            if watcher_name in ("N/A", "default", None) and strategy_name not in ("N/A", "default", None, ""):
                strat_lower = strategy_name.lower()
                if "mtf" in strat_lower or "trend" in strat_lower:
                    watcher_name = "TrendMTFWatcher"
                elif "vwap" in strat_lower or "reversion" in strat_lower or "mean" in strat_lower:
                    watcher_name = "MarketPulseWatcher"
                elif "breakout" in strat_lower or "volatility" in strat_lower:
                    watcher_name = "VolatilityWatcher"
                elif "liquidity" in strat_lower:
                    watcher_name = "LiquidityWatcher"
                elif "oi" in strat_lower or "sweep" in strat_lower:
                    watcher_name = "OrderFlowWSWatcher"
                elif "reversal" in strat_lower or "tick" in strat_lower:
                    watcher_name = "TickWatcherAdapter"

            # Select side emoji
            side_upper = side_name.upper()
            side_emoji = "🟩" if "BUY" in side_upper or "LONG" in side_upper else "🟥" if "SELL" in side_upper or "SHORT" in side_upper else "⬜"

            # Escape special characters to prevent Telegram HTML parse errors
            def escape_html(val):
                return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            symbol_esc = escape_html(symbol)
            exchange_esc = escape_html(exchange_name)
            side_name_esc = escape_html(side_name)
            quantity_esc = escape_html(quantity)
            price_amount_esc = escape_html(price_amount)
            watcher_name_esc = escape_html(watcher_name)
            strategy_name_esc = escape_html(strategy_name)
            regime_context_esc = escape_html(regime_context)
            confidence_esc = escape_html(confidence_str)
            perf_score_esc = escape_html(perf_score_str)
            risk_adj_score_esc = escape_html(risk_adj_score_str)
            sl_value_esc = escape_html(sl_value)
            tp_value_esc = escape_html(tp_value)
            order_time_esc = escape_html(order_time_str)
            order_id_esc = escape_html(order_id)

            message = (f"📦 <b>Order Details:</b>\n"
                       f" ├ <b>Side:</b> {side_emoji} <b>{side_name_esc}</b>\n"
                       f" ├ <b>Symbol:</b> <code>{symbol_esc}</code>\n"
                       f" ├ <b>Exchange:</b> <code>{exchange_esc}</code>\n"
                       f" ├ <b>Quantity:</b> <code>{quantity_esc}</code>\n"
                       f" └ <b>Price:</b> <code>{price_amount_esc}</code>\n\n"
                       f"⚙️ <b>Execution Details:</b>\n"
                       f" ├ <b>Watcher:</b> <code>{watcher_name_esc}</code>\n"
                       f" ├ <b>Strategy:</b> <code>{strategy_name_esc}</code>\n"
                       f" ├ <b>Regime:</b> <code>{regime_context_esc}</code>\n"
                       f" ├ <b>Confidence:</b> <code>{confidence_esc}</code>\n"
                       f" ├ <b>Performance Score:</b> <code>{perf_score_esc}</code>\n"
                       f" └ <b>Risk-Adjusted Priority:</b> <code>{risk_adj_score_esc}</code>\n\n"
                       f"🛡️ <b>Risk Parameters:</b>\n"
                       f" ├ <b>Stop Loss:</b> <code>{sl_value_esc}</code>\n"
                       f" └ <b>Take Profit:</b> <code>{tp_value_esc}</code>\n\n"
                       f"🕒 <b>Time:</b> <code>{order_time_esc}</code>\n"
                       f"🆔 <b>Order ID:</b> <code>{order_id_esc}</code>")

            subject = f"🚀 {symbol} {side_name} on {exchange_name}"

            # Send the notification
            success = telegram_service.send_notification(message, subject, "info", parse_mode="HTML")

            if success:
                self.logger.info(f"🔔 Telegram notification sent for order {order_id}")
            else:
                self.logger.warning(f"⚠️ Failed to send Telegram notification for order {order_id}")

        except Exception as e:
            self.logger.error(f"❌ Error sending Telegram notification: {e}")

    def _lookup_order(self, order_id: str):
        """Return (exchange, symbol) for a placed order_id, or (None, None) if unknown."""
        with self._order_map_lock:
            return self._order_exchange_map.get(str(order_id), (None, None))

    def cancel_order(self, order_id: str) -> bool:
        """B5: cancel via the originating exchange, looked up from the order->exchange map."""
        exchange, symbol = self._lookup_order(order_id)
        if exchange is None or exchange not in self.brokers:
            self.logger.error(f"❌ Cannot cancel {order_id}: no exchange mapping (unknown order)")
            return False
        try:
            ok = bool(self.brokers[exchange].cancel_order(order_id, symbol))
            self.logger.info(f"Cancel {order_id} on {exchange.upper()}: {ok}")
            return ok
        except Exception as e:
            self.logger.error(f"Error canceling {order_id} on {exchange.upper()}: {e}")
            return False

    def get_execution_status(self, execution_id: str) -> str:
        """B5: real status via the originating exchange's adapter (looked up from the map).

        B6: the status read (idempotent) is retried with bounded backoff on transient faults.
        """
        exchange, symbol = self._lookup_order(execution_id)
        if exchange is None or exchange not in self.brokers:
            self.logger.warning(f"Cannot get status for {execution_id}: no exchange mapping")
            return "unknown"
        try:
            from shared.retry import retry_with_backoff
            return retry_with_backoff(
                lambda: self.brokers[exchange].get_order_status(execution_id, symbol),
                max_attempts=3, base_delay=0.5,
                on_retry=lambda a, e, d: self.logger.warning(
                    f"status read for {execution_id} failed (attempt {a}): {e}; retrying in {d}s"))
        except Exception as e:
            self.logger.error(f"Error getting status for {execution_id} on {exchange.upper()}: {e}")
            return "unknown"

    def get_position(self, symbol):
        """
        Get position for a symbol across the appropriate exchange.
        """
        from domain.value_objects import Symbol as DomainSymbol
        symbol_obj = symbol if hasattr(symbol, 'value') else DomainSymbol(str(symbol))
        symbol_str = symbol_obj.value

        exchange_name = self._find_best_exchange_for_symbol(symbol_str)
        if exchange_name:
            broker = self.brokers.get(exchange_name)
            if broker and hasattr(broker, 'get_position'):
                try:
                    return broker.get_position(symbol_obj)
                except Exception as e:
                    self.logger.warning(f"Error getting position for {symbol_str} on {exchange_name}: {e}")
        
        # Fallback: check all brokers
        for name, broker in self.brokers.items():
            if hasattr(broker, 'get_position'):
                try:
                    pos = broker.get_position(symbol_obj)
                    if pos is not None:
                        return pos
                except:
                    continue
        return None
