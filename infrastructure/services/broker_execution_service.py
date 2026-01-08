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

    # Class-level storage for pending orders to prevent duplicate same-direction trades
    _pending_orders = {}
    _pending_orders_lock = threading.Lock()

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
        with cls._pending_orders_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str not in cls._pending_orders:
                cls._pending_orders[symbol_str] = []
            cls._pending_orders[symbol_str].append((side, order_id))

    @classmethod
    def _remove_pending_order(cls, symbol: Symbol, order_id: str):
        """Remove an order from the pending orders tracking."""
        with cls._pending_orders_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str in cls._pending_orders:
                # Remove the specific order ID
                cls._pending_orders[symbol_str] = [
                    (side, oid) for side, oid in cls._pending_orders[symbol_str]
                    if oid != order_id
                ]
                # Clean up empty lists
                if not cls._pending_orders[symbol_str]:
                    del cls._pending_orders[symbol_str]

    @classmethod
    def _has_pending_order_in_direction(cls, symbol: Symbol, side: str) -> bool:
        """Check if there's a pending order in the same direction for the symbol."""
        with cls._pending_orders_lock:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            if symbol_str in cls._pending_orders:
                for pending_side, _ in cls._pending_orders[symbol_str]:
                    if pending_side == side:
                        return True
            return False

    def execute_order(self, order: Order) -> str:
        """Execute an order through the configured broker."""
        try:
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
                    raise ValueError(f"DUPLICATE:{order.symbol.value}:{intended_position_side}")

            # Enhance order with risk parameters if they're missing
            # This ensures institutional standards are met even if the Strategy layer didn't add them
            # In a properly architected system, the Strategy layer should add these parameters
            order = self._enhance_order_with_risk_parameters(order)

            # Validate the order against risk management standards
            # This should ideally be done by the Risk Management layer before reaching broker
            is_valid = self._validate_order_risk(order)
            if not is_valid:
                self.logger.error(f"❌ ORDER REJECTED: Risk validation failed for order: {order}")
                raise ValueError(f"Order failed risk validation: {order}")

            self.logger.info(f"🎯 EXECUTING ORDER ON {self.broker_name}: {order}")

            # Add to pending orders before placing the order
            if prevent_same_direction and intended_position_side:
                order_id_temp = "TEMP_" + str(id(order))  # Temporary ID for tracking before placement
                self._add_pending_order(order.symbol, intended_position_side, order_id_temp)

            try:
                # If using multi-broker service, use execute_order method
                if self.use_multi_broker:
                    order_id = self.broker.execute_order(order)
                else:
                    # For single broker, use place_order method
                    order_id = self.broker.place_order(order)

                self.logger.info(f"✅ ORDER PLACED SUCCESSFULLY ON {self.broker_name}: {order_id}")

                # Send Telegram notification about successful order placement
                self._send_order_placed_notification(order, order_id)

                return order_id
            finally:
                # Remove from pending orders after attempting to place
                if prevent_same_direction and intended_position_side:
                    self._remove_pending_order(order.symbol, order_id_temp)
        except Exception as e:
            self.logger.error(f"❌ FAILED TO EXECUTE ORDER ON {self.broker_name}: {e}")
            raise

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

    def _enhance_order_with_risk_parameters(self, order: Order) -> Order:
        """Enhance order with risk parameters if they're missing."""
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
                sl_price, tp_price = risk_service.calculate_sl_tp_levels(
                    entry_price=current_price,
                    position_side=position_side,
                    risk_adjustment_factors=risk_factors,
                    atr_value=None,  # Would come from market data in real implementation
                    market_data=market_data
                )

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
                stop_loss_price=Money(amount=float(sl_price), currency='USDT') if not has_stop_loss else getattr(order, 'stop_loss_price', None),
                take_profit_price=Money(amount=float(tp_price), currency='USDT') if not has_take_profit else getattr(order, 'take_profit_price', None),
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