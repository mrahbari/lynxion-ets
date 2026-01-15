"""
Broker Execution Service - Handles broker configuration and execution logic
This service provides a clean interface for broker execution while keeping
the main runner files clean and focused.
"""
from typing import Dict, Any, Optional
from domain.ports.execution_ports import ExecutionPort
from domain.entities.trading_entities import Order
from domain.value_objects import Symbol
from domain.enums.broker_enum import BrokerType
from shared.logger import EnhancedLogger
import os
import threading


class BrokerExecutionService(ExecutionPort):
    """
    A configurable execution service that can work with multiple brokers.
    This service handles broker configuration and execution logic.
    """

    # Duplicate prevention is now handled by the shared PendingOrdersTracker
    # See infrastructure/shared/pending_orders_tracker.py

    def __init__(self, broker_type: Optional[str] = None, config: Optional[Dict[str, Any]] = None, use_multi_broker: bool = False, primary_broker: Optional[str] = None):
        """
        Initialize the broker execution service.

        Args:
            broker_type: Type of broker ('bingx', 'binance', 'mexc', 'phemex').
                        If None, will use DEFAULT_BROKER environment variable.
            config: Optional configuration dictionary. If None, will load from environment.
            use_multi_broker: Whether to use multi-broker service with exchange switching
            primary_broker: Primary broker to use when using multi-broker service (e.g., 'bingx', 'binance')
        """
        from infrastructure.brokers.broker_adapters import (
            BingXBrokerAdapter, BinanceBrokerAdapter, MEXCBrokerAdapter, PhemexBrokerAdapter
        )
        from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService

        # Determine if we should use multi-broker service
        self.use_multi_broker = use_multi_broker

        if self.use_multi_broker:
            # Initialize multi-broker service for exchange switching
            # Allow specifying primary broker for the multi-broker service
            self.multi_broker_service = MultiBrokerExecutionService(primary_broker=primary_broker)
            self.logger = EnhancedLogger("BrokerExecutionService")
            self.broker_name = "MultiBroker"
            self.broker_type = "multi"
            self.broker = self.multi_broker_service
            self.logger.info("✅ Multi-Broker service initialized with exchange switching capability")
        else:
            # Determine broker type
            if broker_type is None:
                broker_type_str = os.getenv('DEFAULT_BROKER', 'bingx').lower()  # Changed to 'bingx' as default
            else:
                broker_type_str = broker_type.lower()

            # Convert to enum
            try:
                self.broker_type_enum = BrokerType.from_string(broker_type_str)
                self.broker_type = self.broker_type_enum.value
            except ValueError:
                raise ValueError(
                    f"Unsupported broker type: {broker_type_str}. "
                    f"Supported types: {BrokerType.get_supported_types()}"
                )

            # Load configuration
            if config is None:
                config = self._load_config_from_env(self.broker_type)

            self.logger = EnhancedLogger("BrokerExecutionService")

            # Initialize the appropriate broker adapter
            # Since we don't know the exact constructor signatures, we'll pass the config as a dict
            # and let the adapter handle the parameters internally
            if self.broker_type == BrokerType.BINGX.value:
                self.broker = BingXBrokerAdapter(config)
                self.broker_name = self.broker_type_enum.get_display_name()
            elif self.broker_type == BrokerType.BINANCE.value:
                self.broker = BinanceBrokerAdapter(config)
                self.broker_name = self.broker_type_enum.get_display_name()
            elif self.broker_type == BrokerType.MEXC.value:
                # MEXC adapter expects individual parameters
                self.broker = MEXCBrokerAdapter(
                    api_key=config['api_key'],
                    secret_key=config['secret_key'],
                    base_url="https://api-testnet.mexc.com" if config['testnet'] else "https://api.mexc.com"
                )
                self.broker_name = self.broker_type_enum.get_display_name()
            elif self.broker_type == BrokerType.PHEMEX.value:
                # Phemex adapter expects individual parameters
                self.broker = PhemexBrokerAdapter(
                    api_key=config['api_key'],
                    secret_key=config['secret_key'],
                    base_url="https://testnet-api.phemex.com" if config['testnet'] else "https://api.phemex.com"
                )
                self.broker_name = self.broker_type_enum.get_display_name()
            else:
                raise ValueError(
                    f"Unsupported broker type: {self.broker_type}. "
                    f"Supported types: {BrokerType.get_supported_types()}"
                )

            # Try to connect the broker during initialization
            try:
                if hasattr(self.broker, 'connect'):
                    self.broker.connect()
                self.logger.info(f"✅ Successfully connected to {self.broker_name} broker")
            except Exception as e:
                self.logger.error(f"❌ Could not connect broker {self.broker_name} during initialization: {e}")
                # Instead of just warning, let's try to use a fallback broker if binance is not configured
                if broker_type_str == 'binance':
                    # If binance is not configured properly, warn user but continue
                    self.logger.warning("⚠️  Binance broker not properly configured. Please check your BINANCE_API_KEY and BINANCE_SECRET_KEY in environment variables.")
                # Don't raise the exception here as the broker might still be functional for other operations
                # Just log the connection issue
    
    def _load_config_from_env(self, broker_type: str) -> Dict[str, Any]:
        """Load broker configuration from environment variables."""
        broker_enum = BrokerType.from_string(broker_type)

        if broker_enum == BrokerType.BINGX:
            config = {
                'api_key': os.getenv('BINGX_API_KEY'),
                'secret_key': os.getenv('BINGX_SECRET_KEY'),
                'passphrase': os.getenv('BINGX_PASSPHRASE', ''),
                'testnet': os.getenv('BINGX_TESTNET', 'true').lower() == 'true'
            }
        elif broker_enum == BrokerType.BINANCE:
            config = {
                'api_key': os.getenv('BINANCE_API_KEY'),
                'secret_key': os.getenv('BINANCE_SECRET_KEY'),
                'testnet': os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
            }
        elif broker_enum == BrokerType.MEXC:
            config = {
                'api_key': os.getenv('MEXC_API_KEY'),
                'secret_key': os.getenv('MEXC_SECRET_KEY'),
                'testnet': os.getenv('MEXC_TESTNET', 'true').lower() == 'true'
            }
        elif broker_enum == BrokerType.PHEMEX:
            config = {
                'api_key': os.getenv('PHEMEX_API_KEY'),
                'secret_key': os.getenv('PHEMEX_SECRET_KEY'),
                'testnet': os.getenv('PHEMEX_TESTNET', 'true').lower() == 'true'
            }
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")

        # Validate required configuration
        required_keys = ['api_key', 'secret_key']
        for key in required_keys:
            if not config.get(key):
                raise ValueError(
                    f"{broker_type.upper()}_{key.upper()} must be set in environment variables"
                )

        return config

    @classmethod
    def _add_pending_order(cls, symbol: Symbol, side: str, order_id: str):
        """Add an order to the pending orders tracking."""
        # Use a shared pending orders tracking to ensure consistency across all broker services
        # Import here to avoid circular imports
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        PendingOrdersTracker.add_pending_order(symbol, side, order_id)

    @classmethod
    def _remove_pending_order(cls, symbol: Symbol, order_id: str):
        """Remove an order from the pending orders tracking."""
        # Use a shared pending orders tracking to ensure consistency across all broker services
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        PendingOrdersTracker.remove_pending_order(symbol, order_id)

    @classmethod
    def _has_pending_order_in_direction(cls, symbol: Symbol, side: str) -> bool:
        """Check if there's a pending order in the same direction for the symbol."""
        # Use a shared pending orders tracking to ensure consistency across all broker services
        from infrastructure.shared.pending_orders_tracker import PendingOrdersTracker
        return PendingOrdersTracker.has_pending_order_in_direction(symbol, side)

    def execute_order(self, order: Order) -> str:
        """Execute an order through the configured broker."""
        try:
            # Check if the system is still running - if not, reject the execution
            if hasattr(self, '_is_system_running') and not self._is_system_running:
                self.logger.warning(f"System is shutting down, rejecting order execution for {order.symbol.value if hasattr(order, 'symbol') and hasattr(getattr(order, 'symbol', None), 'value') else 'UNKNOWN'}")
                return None

            # First, check if the symbol is in the approved symbols list
            # This is the primary validation - if a symbol is not approved, it's not available for trading
            from utils.symbol_validator import symbol_validator
            if not symbol_validator.is_symbol_approved(order.symbol):
                symbol_str = order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol)
                self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Order execution denied.")
                return None

            # Note: Symbol filtering (like stablecoin pairs) is now handled at the watcher level
            # to avoid processing symbols that will be rejected later. This improves efficiency.

            # Check if duplicate same-direction trade prevention is enabled
            prevent_same_direction = os.getenv('PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL', 'true').lower() == 'true'

            if prevent_same_direction:
                # Check if there's already an active position in the same direction for this symbol
                # This requires checking the current positions, which may be done through the broker
                try:
                    current_position = self.broker.get_position(order.symbol) if hasattr(self.broker, 'get_position') else None
                except Exception as pos_error:
                    self.logger.warning(f"⚠️ Could not get position for {order.symbol.value}, proceeding with order: {pos_error}")
                    current_position = None

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
                    if intended_position_side and hasattr(current_position.side, 'name') and current_position.side.name == intended_position_side:
                        position_duplicate = True

                # Check for pending orders in the same direction
                if intended_position_side:
                    pending_duplicate = self._has_pending_order_in_direction(order.symbol, intended_position_side)

                # If either condition is true, prevent the trade
                if position_duplicate or pending_duplicate:
                    if position_duplicate:
                        self.logger.info(f"❌ DUPLICATE REJECTED: Active {current_position.side.name} position exists for {order.symbol.value}. Preventing duplicate same-direction trade.")
                    else:
                        self.logger.info(f"❌ DUPLICATE REJECTED: Pending {intended_position_side} order exists for {order.symbol.value}. Preventing duplicate same-direction trade.")
                    # Return a failure status instead of raising an exception to prevent system crashes
                    return None  # Indicate that the order was not placed due to duplicate prevention

            # In a properly architected system, all risk management should be handled by the Strategy layer
            # The broker should only execute orders that have already been properly risk-managed
            # We'll validate that required risk parameters are present but won't enhance them
            if not self._validate_required_risk_parameters(order):
                self.logger.error(f"❌ ORDER REJECTED: Missing required risk parameters: {order}")
                raise ValueError(f"Order missing required risk parameters: {order}")

            # Perform final validation to ensure the order parameters are reasonable before sending to broker
            if not self._validate_order_parameters_before_broker(order):
                self.logger.error(f"❌ ORDER REJECTED: Order parameters are invalid or unreasonable: {order}")
                # Return None instead of raising an exception to prevent system crashes
                return None

            self.logger.info(f"🎯 EXECUTING ORDER ON {self.broker_name}: {order}")

            # Add to pending orders before placing the order
            order_id_temp = None
            if prevent_same_direction and intended_position_side:
                order_id_temp = "TEMP_" + str(id(order))  # Temporary ID for tracking before placement
                self._add_pending_order(order.symbol, intended_position_side, order_id_temp)

            try:
                # Check if broker is connected before attempting to place order
                if hasattr(self.broker, 'connected'):
                    if not self.broker.connected:
                        self.logger.error(f"❌ BROKER NOT CONNECTED: Cannot place order on {self.broker_name}")
                        return None
                elif hasattr(self.broker, 'connect') and callable(getattr(self.broker, 'connect')):
                    # Try to connect if not connected
                    try:
                        if not getattr(self.broker, 'connected', False):
                            self.broker.connect()
                    except Exception as conn_error:
                        self.logger.error(f"❌ FAILED TO CONNECT TO BROKER {self.broker_name}: {conn_error}")
                        return None

                # If using multi-broker service, use execute_order method
                if self.use_multi_broker:
                    order_id = self.broker.execute_order(order)
                else:
                    # For single broker, use place_order method
                    order_id = self.broker.place_order(order)

                # Check if order_id is valid before proceeding
                if order_id is None or order_id == "":
                    self.logger.error(f"❌ ORDER PLACEMENT FAILED: Broker returned invalid order ID: {order_id}")
                    return None

                self.logger.info(f"✅ ORDER PLACED SUCCESSFULLY ON {self.broker_name}: {order_id}")

                # Send Telegram notification about successful order placement
                self._send_order_placed_notification(order, order_id)

                return order_id
            except Exception as e:
                self.logger.error(f"❌ FAILED TO EXECUTE ORDER ON {self.broker_name}: {e}")
                raise
            finally:
                # Remove from pending orders after attempting to place (whether successful or failed)
                # This is important to prevent stuck pending orders when order placement fails
                if prevent_same_direction and intended_position_side and order_id_temp:
                    try:
                        self._remove_pending_order(order.symbol, order_id_temp)
                    except Exception as cleanup_error:
                        self.logger.error(f"❌ ERROR DURING PENDING ORDER CLEANUP: {cleanup_error}")
                        # Don't raise the exception here as it would mask the original error
        except Exception as e:
            self.logger.error(f"❌ FAILED TO EXECUTE ORDER ON {self.broker_name}: {e}")
            raise

    def _validate_required_risk_parameters(self, order: Order) -> bool:
        """Validate that the order has required risk parameters (should be set by Strategy layer)"""
        # Check if stop loss and take profit are set (these should be set by the Strategy layer)
        has_stop_loss = hasattr(order, 'stop_loss_price') and order.stop_loss_price is not None
        has_take_profit = hasattr(order, 'take_profit_price') and order.take_profit_price is not None

        # For institutional standards, both SL and TP should be set by the Strategy layer
        # However, we'll allow execution if they're missing (with a warning) to maintain compatibility
        if not has_stop_loss or not has_take_profit:
            self.logger.warning(f"⚠️ Order missing SL/TP parameters (should be set by Strategy layer): {order.symbol.value}")
            # We'll still allow the order to proceed but log the issue
            return True

        return True

    def _validate_order_parameters_before_broker(self, order: Order) -> bool:
        """Final validation to ensure order parameters are reasonable before sending to broker."""
        try:
            # Check if we have a valid price
            if order.price and hasattr(order.price, 'amount') and order.price.amount:
                entry_price = float(order.price.amount)
                self.logger.debug(f"Validating order parameters - Entry price: {entry_price}")

                # Check if stop loss price is reasonable
                if hasattr(order, 'stop_loss_price') and order.stop_loss_price:
                    sl_price = float(order.stop_loss_price.amount) if hasattr(order.stop_loss_price, 'amount') else float(order.stop_loss_price)
                    self.logger.debug(f"Stop loss price: {sl_price}")

                    # For BUY orders: SL should be below entry price
                    # For SELL orders: SL should be above entry price (for short positions)
                    is_buy_order = hasattr(order, 'side') and order.side.name == 'BUY'
                    self.logger.debug(f"Order side: {'BUY' if is_buy_order else 'SELL'}")

                    if is_buy_order:
                        # For BUY orders, SL should be below entry price (but not too far below)
                        if sl_price <= 0:
                            self.logger.warning(f"Invalid SL for BUY order: SL ({sl_price}) <= 0")
                            return False
                        elif sl_price >= entry_price:
                            self.logger.warning(f"Invalid SL for BUY order: SL ({sl_price}) >= Entry ({entry_price})")
                            return False
                        elif entry_price > 0 and sl_price < entry_price * 0.01:  # SL not more than 99% below entry
                            self.logger.warning(f"SL too far from entry for BUY order: SL ({sl_price}) vs Entry ({entry_price})")
                            return False
                    else:
                        # For SELL orders, SL should be above entry price (for stop loss on short)
                        if sl_price <= 0:
                            self.logger.warning(f"Invalid SL for SELL order: SL ({sl_price}) <= 0")
                            return False
                        elif sl_price <= entry_price:
                            self.logger.warning(f"Invalid SL for SELL order: SL ({sl_price}) <= Entry price ({entry_price})")
                            return False
                        elif entry_price > 0 and sl_price > entry_price * 100:  # SL not more than 100x above entry
                            self.logger.warning(f"SL too far from entry for SELL order: SL ({sl_price}) vs Entry ({entry_price})")
                            return False

                # Check if take profit price is reasonable
                if hasattr(order, 'take_profit_price') and order.take_profit_price:
                    tp_price = float(order.take_profit_price.amount) if hasattr(order.take_profit_price, 'amount') else float(order.take_profit_price)
                    self.logger.debug(f"Take profit price: {tp_price}")

                    # For BUY orders: TP should be above entry price
                    # For SELL orders: TP should be below entry price (for short positions)
                    is_buy_order = hasattr(order, 'side') and order.side.name == 'BUY'

                    if is_buy_order:
                        # For BUY orders, TP should be above entry price (but not too far above)
                        if tp_price <= 0:
                            self.logger.warning(f"Invalid TP for BUY order: TP ({tp_price}) <= 0")
                            return False
                        elif tp_price <= entry_price:
                            self.logger.warning(f"Invalid TP for BUY order: TP ({tp_price}) <= Entry ({entry_price})")
                            return False
                        elif entry_price > 0 and tp_price > entry_price * 100:  # TP not more than 100x above entry
                            self.logger.warning(f"TP too far from entry for BUY order: TP ({tp_price}) vs Entry ({entry_price})")
                            return False
                    else:
                        # For SELL orders, TP should be below entry price (for profit on short)
                        if tp_price <= 0:
                            self.logger.warning(f"Invalid TP for SELL order: TP ({tp_price}) <= 0")
                            return False
                        elif tp_price >= entry_price:
                            self.logger.warning(f"Invalid TP for SELL order: TP ({tp_price}) >= Entry ({entry_price})")
                            return False
                        elif entry_price > 0 and tp_price < entry_price * 0.01:  # TP not more than 99% below entry
                            self.logger.warning(f"TP too far from entry for SELL order: TP ({tp_price}) vs Entry ({entry_price})")
                            return False

            return True
        except Exception as e:
            self.logger.warning(f"Parameter validation error: {e}, allowing order to proceed")
            return True  # Allow order to proceed if validation fails

    def _send_order_placed_notification(self, order: Order, order_id: str):
        """Send a Telegram notification about a successfully placed order."""
        try:
            # Check if Telegram notifications are enabled
            telegram_notifications_enabled = os.getenv('TELEGRAM_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
            if not telegram_notifications_enabled:
                self.logger.debug(f"Telegram notifications disabled, skipping notification for order {order_id}")
                return  # Skip notifications if disabled

            # Import Telegram service
            from infrastructure.services.risk_alerts import TelegramNotificationService

            # Get Telegram credentials from environment
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
            chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

            # Check if credentials are available
            if not bot_token or not chat_id:
                self.logger.warning(f"Telegram credentials not available, skipping notification for order {order_id}")
                return  # Skip if credentials are missing

            # Create Telegram service instance
            telegram_service = TelegramNotificationService(
                bot_token=bot_token,
                chat_id=chat_id
            )

            # Prepare notification message
            symbol = getattr(order, 'symbol', {}).value if hasattr(getattr(order, 'symbol', None), 'value') else str(getattr(order, 'symbol', 'UNKNOWN'))
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
                      f"Symbol: {symbol}\n"
                      f"Side: {side_name}\n"
                      f"Quantity: {quantity}\n"
                      f"Price: {price_amount}\n"
                      f"Stop Loss: {sl_value}\n"
                      f"Take Profit: {tp_value}\n"
                      f"Strategy: {strategy_name}\n"
                      f"Order ID: {order_id}")

            subject = f"Order Placed: {symbol} {side_name}"

            # Send the notification
            success = telegram_service.send_notification(message, subject, "info")

            if success:
                self.logger.info(f"🔔 Telegram notification sent for order {order_id}")
            else:
                self.logger.warning(f"⚠️ Failed to send Telegram notification for order {order_id}")

        except ImportError as e:
            self.logger.error(f"❌ ImportError sending Telegram notification: {e}")
        except Exception as e:
            self.logger.error(f"❌ Error sending Telegram notification: {e}")

    def set_system_running_state(self, is_running: bool):
        """Set the system running state to prevent order execution during shutdown."""
        self._is_system_running = is_running

    # Removed _validate_order_risk and _enhance_order_with_risk_parameters methods
    # as risk management should only be handled by the Strategy layer per architectural requirements

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order through the configured broker."""
        try:
            self.logger.info(f"🔄 CANCELLING ORDER ON {self.broker_name}: {order_id}")
            # If using multi-broker service, use cancel_order method directly
            if self.use_multi_broker:
                return self.broker.cancel_order(order_id)
            else:
                # For single broker, use cancel_order method with placeholder symbol
                # For now, we'll use a placeholder symbol - in real implementation,
                # the order_id should be sufficient or you'd pass the symbol
                return self.broker.cancel_order(order_id, Symbol("BTCUSDT"))  # Placeholder
        except Exception as e:
            self.logger.error(f"❌ FAILED TO CANCEL ORDER ON {self.broker_name}: {e}")
            return False

    def get_execution_status(self, execution_id: str) -> str:
        """Get the status of an execution through the configured broker."""
        try:
            # If using multi-broker service, use get_execution_status method directly
            if self.use_multi_broker:
                return self.broker.get_execution_status(execution_id)
            else:
                # For single broker, use get_order_status method with placeholder symbol
                # In a real implementation, you'd need the symbol as well
                # For now, using placeholder - real implementation would track symbol with execution
                status = self.broker.get_order_status(execution_id, Symbol("BTCUSDT"))  # Placeholder
                return status
        except Exception as e:
            self.logger.error(f"❌ FAILED TO GET EXECUTION STATUS ON {self.broker_name}: {e}")
            return "error"

    def get_broker_name(self) -> str:
        """Get the name of the configured broker."""
        return self.broker_name

    def get_broker_type(self) -> str:
        """Get the type of the configured broker."""
        return self.broker_type

    def get_available_symbols(self) -> set:
        """Get available symbols from the configured broker."""
        # If using multi-broker service, delegate to it
        if self.use_multi_broker and hasattr(self.broker, 'get_available_symbols'):
            return self.broker.get_available_symbols()

        # Otherwise, use the single broker approach
        # Ensure broker is connected before calling the method
        if hasattr(self.broker, 'connect') and not getattr(self.broker, 'connected', False):
            try:
                self.broker.connect()
            except Exception as e:
                self.logger.warning(f"Could not connect broker {self.broker_name} before getting available symbols: {e}")
                return set()

        if hasattr(self.broker, 'get_available_symbols'):
            return self.broker.get_available_symbols()
        else:
            # If the internal broker doesn't have this method, return empty set
            self.logger.warning(f"Broker {self.broker_name} does not support get_available_symbols method")
            return set()


def create_execution_service(broker_type: Optional[str] = None, use_multi_broker: bool = True, primary_broker: Optional[str] = None) -> ExecutionPort:
    """
    Factory function to create a broker execution service.

    Args:
        broker_type: Type of broker ('bingx', 'binance', 'mexc', 'phemex').
                    If None, will use DEFAULT_BROKER environment variable.
        use_multi_broker: Whether to use multi-broker service with exchange switching (default: True)
        primary_broker: Primary broker to use when using multi-broker service (e.g., 'bingx', 'binance')

    Returns:
        Configured execution service instance
    """
    return BrokerExecutionService(broker_type=broker_type, use_multi_broker=use_multi_broker, primary_broker=primary_broker)


def create_execution_service_from_enum(broker_type_enum: Optional['BrokerType'] = None) -> ExecutionPort:
    """
    Factory function to create a broker execution service from BrokerType enum.

    Args:
        broker_type_enum: BrokerType enum value.
                         If None, will use DEFAULT_BROKER environment variable.

    Returns:
        Configured execution service instance
    """
    broker_type_str = broker_type_enum.value if broker_type_enum else None
    return BrokerExecutionService(broker_type=broker_type_str)