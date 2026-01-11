"""
Event system for proper signal routing between architectural layers.
Following correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
import os
from typing import Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
import queue
from domain.entities.signal_entities import MarketObservation, InterpretedSignal, FusedSignal, ExecutionIntent


class EventType(Enum):
    MARKET_OBSERVATION = "market_observation"
    INTERPRETED_SIGNAL = "interpreted_signal"
    FUSED_SIGNAL = "fused_signal"
    EXECUTION_INTENT = "execution_intent"
    TRADE_EXECUTION = "trade_execution"


@dataclass
class SignalEvent:
    """Event containing a signal to be routed through the system"""
    event_type: EventType
    data: Any
    timestamp: datetime = None
    source_component: str = None
    correlation_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventRouter:
    """Routes events between architectural layers with proper separation of concerns"""

    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_queue = queue.Queue()
        self.running = False
        self.router_thread = None
        self._lock = threading.Lock()

    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe a handler to a specific event type"""
        with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe a handler from a specific event type"""
        with self._lock:
            if event_type in self.subscribers:
                try:
                    self.subscribers[event_type].remove(handler)
                except ValueError:
                    pass  # Handler was not subscribed

    def publish(self, event: SignalEvent):
        """Publish an event to the routing system"""
        self.event_queue.put(event)

    def publish_observation(self, observation: MarketObservation, source: str = None, correlation_id: str = None):
        """Publish a market observation event"""
        event = SignalEvent(
            event_type=EventType.MARKET_OBSERVATION,
            data=observation,
            source_component=source,
            correlation_id=correlation_id
        )
        self.publish(event)

    def publish_interpreted_signal(self, signal: InterpretedSignal, source: str = None, correlation_id: str = None):
        """Publish an interpreted signal event"""
        event = SignalEvent(
            event_type=EventType.INTERPRETED_SIGNAL,
            data=signal,
            source_component=source,
            correlation_id=correlation_id
        )
        self.publish(event)

    def publish_fused_signal(self, signal: FusedSignal, source: str = None, correlation_id: str = None):
        """Publish a fused signal event"""
        event = SignalEvent(
            event_type=EventType.FUSED_SIGNAL,
            data=signal,
            source_component=source,
            correlation_id=correlation_id
        )
        self.publish(event)

    def publish_execution_intent(self, intent: ExecutionIntent, source: str = None, correlation_id: str = None):
        """Publish an execution intent event"""
        event = SignalEvent(
            event_type=EventType.EXECUTION_INTENT,
            data=intent,
            source_component=source,
            correlation_id=correlation_id
        )
        self.publish(event)

    def start(self):
        """Start the event routing thread"""
        if not self.running:
            self.running = True
            self.router_thread = threading.Thread(target=self._process_events, daemon=True)
            self.router_thread.start()

    def stop(self):
        """Stop the event routing system"""
        self.running = False
        if self.router_thread:
            self.router_thread.join(timeout=2.0)

    def _process_events(self):
        """Process events from the queue and route them to subscribers"""
        while self.running:
            try:
                event = self.event_queue.get(timeout=1.0)
                self._route_event(event)
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing event: {e}")

    def _route_event(self, event: SignalEvent):
        """Route an event to all subscribers of its type"""
        if event.event_type in self.subscribers:
            for handler in self.subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler for {event.event_type}: {e}")


class SignalProcessor:
    """Processes signals through the proper architectural layers"""

    def __init__(self, event_router: EventRouter):
        self.event_router = event_router
        self.logger = None  # Will be set by calling component

    def setup_signal_processing(self, engine_service, fusion_service, strategy_manager, execution_service):
        """Setup the proper signal processing chain"""
        # Subscribe handlers to process each type of event
        self.event_router.subscribe(EventType.MARKET_OBSERVATION, 
                                  lambda event: self._process_observation(event, engine_service))
        self.event_router.subscribe(EventType.INTERPRETED_SIGNAL, 
                                  lambda event: self._process_interpreted_signal(event, fusion_service))
        self.event_router.subscribe(EventType.FUSED_SIGNAL, 
                                  lambda event: self._process_fused_signal(event, strategy_manager))
        self.event_router.subscribe(EventType.EXECUTION_INTENT, 
                                  lambda event: self._process_execution_intent(event, execution_service))

    def _process_observation(self, event: SignalEvent, engine_service):
        """Process market observation through engine layer"""
        try:
            observation = event.data
            if self.logger:
                self.logger.info(f"Processing observation from {event.source_component} for {observation.symbol.value}")
            
            # Process observation through engine
            interpreted_signal = engine_service.process_observation(observation)
            
            if interpreted_signal:
                # Publish interpreted signal for next layer
                self.event_router.publish_interpreted_signal(
                    interpreted_signal, 
                    source="EngineService",
                    correlation_id=event.correlation_id
                )
                if self.logger:
                    self.logger.info(f"Published interpreted signal: {interpreted_signal.signal_type.value} for {interpreted_signal.symbol.value}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing observation: {e}")

    def _process_interpreted_signal(self, event: SignalEvent, fusion_service):
        """Process interpreted signal through fusion layer"""
        try:
            signal = event.data
            if self.logger:
                self.logger.info(f"Processing interpreted signal from {event.source_component} for {signal.symbol.value}")
            
            # Process signal through fusion (we need to pass it as a list)
            fused_signal = fusion_service.fuse_signals([signal])
            
            if fused_signal:
                # Publish fused signal for next layer
                self.event_router.publish_fused_signal(
                    fused_signal,
                    source="FusionService", 
                    correlation_id=event.correlation_id
                )
                if self.logger:
                    self.logger.info(f"Published fused signal: {fused_signal.dominant_bias.value} for {fused_signal.symbol.value}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing interpreted signal: {e}")

    def _process_fused_signal(self, event: SignalEvent, strategy_manager):
        """Process fused signal through strategy layer"""
        try:
            fused_signal = event.data
            if self.logger:
                self.logger.info(f"Forwarding fused signal from {event.source_component} for {fused_signal.symbol.value} to aggregator")

            # The signal aggregator is already subscribed to FUSED_SIGNAL events
            # and will handle batch collection and evaluation of signals
            # This ensures we compare opportunities across all symbols before executing
            # The aggregator will handle the strategy evaluation and execution intent generation

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error forwarding fused signal to aggregator: {e}")

    def _process_execution_intent(self, event: SignalEvent, execution_service):
        """Process execution intent through broker layer"""
        try:
            execution_intent = event.data
            if self.logger:
                self.logger.info(f"📥 RECEIVED EXECUTION INTENT: Processing execution intent from {event.source_component} for {execution_intent.symbol.value} with confidence {float(execution_intent.intent_confidence.value):.2%}")

            # Check if we have access to the orchestrator to queue the execution intent
            # The orchestrator should be accessible through the global architecture orchestrator
            from infrastructure.orchestrators.architecture_orchestrator import architecture_orchestrator

            # If the architecture orchestrator has an execution service, use it
            # Otherwise, use the execution service passed as a parameter
            if hasattr(architecture_orchestrator, 'execution_service') and architecture_orchestrator.execution_service:
                execution_service_to_use = architecture_orchestrator.execution_service
                if self.logger:
                    self.logger.info(f"Using execution service from architecture orchestrator for {execution_intent.symbol.value}")
            else:
                execution_service_to_use = execution_service
                if self.logger:
                    self.logger.info(f"Using execution service from parameter for {execution_intent.symbol.value}")

            # Use the execution service directly to execute the order
            from domain.entities.signal_entities import Order, OrderSide
            from domain.value_objects import Money
            from decimal import Decimal

            # Create order from execution intent
            # Get current price for the symbol to determine position size
            current_price = None
            if hasattr(execution_service_to_use, 'get_current_price'):
                try:
                    current_price = execution_service_to_use.get_current_price(execution_intent.symbol)
                except:
                    pass  # Fallback to default price below

            # If we still don't have a price, use a fallback
            if current_price is None or current_price <= 0:
                # Try to get price from exchange directly
                try:
                    import ccxt
                    exchange = ccxt.binance()
                    ticker = exchange.fetch_ticker(execution_intent.symbol.value)
                    current_price = ticker['last'] if 'last' in ticker else ticker['close']
                except:
                    # If all methods fail, use a default price
                    current_price = 50000.0  # Fallback price

            # Calculate quantity based on risk parameters
            risk_params = execution_intent.risk_parameters
            position_size_pct = risk_params.get('max_position_size', 0.02)  # Default 2%

            # Fixed Position Size Configuration (for testing purposes)
            fixed_position_size_enabled = os.getenv('FIXED_POSITION_SIZE_ENABLED', 'false').lower() == 'true'
            fixed_position_amount = float(os.getenv('FIXED_POSITION_AMOUNT', '10.0'))  # Default to $10 for testing

            # Calculate quantity based on risk parameters and account balance
            try:
                if fixed_position_size_enabled:
                    # Use fixed position size for testing
                    # Check if current_price is valid before division
                    if current_price is None or current_price <= 0:
                        # Use fallback price if current_price is invalid
                        fallback_price = 50000.0
                        quantity = fixed_position_amount / fallback_price
                        if self.logger:
                            self.logger.info(f"Using fixed position size with fallback price: ${fixed_position_amount} at ${fallback_price} = {quantity} units")
                    else:
                        quantity = fixed_position_amount / current_price
                        if self.logger:
                            self.logger.info(f"Using fixed position size: ${fixed_position_amount} at ${current_price} = {quantity} units")
                else:
                    # In a real implementation, we'd get portfolio metrics from portfolio service
                    # For now, using a default account balance from environment variable
                    account_balance = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '10000.0'))  # Default to $10,000 if not available
                    position_value = account_balance * position_size_pct

                    # Calculate quantity based on position value and current price
                    # Check if current_price is valid before division
                    if current_price is None or current_price <= 0:
                        # Use fallback price if current_price is invalid
                        fallback_price = 50000.0
                        quantity = position_value / fallback_price
                        if self.logger:
                            self.logger.info(f"Using calculated position size with fallback price: ${position_value} at ${fallback_price} = {quantity} units")
                    else:
                        quantity = position_value / current_price

                    # Apply any quantity adjustments from risk parameters
                    if 'position_quantity' in risk_params:
                        quantity = risk_params['position_quantity']

            except:
                # If portfolio service fails, use a default quantity
                if fixed_position_size_enabled:
                    # Use fixed position size for testing with fallback price
                    fallback_price = 50000.0
                    quantity = fixed_position_amount / fallback_price
                    if self.logger:
                        self.logger.info(f"Using fixed position size (fallback): ${fixed_position_amount} at ${fallback_price} = {quantity} units")
                else:
                    # Use default account balance from environment variable
                    default_account_balance = float(os.getenv('DEFAULT_ACCOUNT_BALANCE', '1000.0'))  # Default to $1,000 if not available
                    fallback_price = 50000.0
                    quantity = position_size_pct * default_account_balance / fallback_price

            # Ensure minimum quantity to avoid issues with small trades
            if quantity < 0.001:
                quantity = 0.001  # Minimum trade size

            # Use the side from the execution intent
            order_side = execution_intent.side

            # Determine position side based on order side for futures trading
            position_side = "LONG" if order_side.name == 'BUY' else "SHORT"

            # Use risk management system to calculate dynamic TP/SL based on market conditions
            from infrastructure.risk.advanced_risk_management import SLTPManager

            # Initialize SL/TP manager with risk parameters
            sltp_manager = SLTPManager(
                sl_activation_pct=risk_params.get('stop_loss_pct', 0.02),  # 2% default SL
                tp_activation_pct=risk_params.get('take_profit_pct', 0.03)  # 3% default TP
            )

            # Calculate dynamic stop loss and take profit prices based on risk parameters
            if order_side.name == 'BUY':
                # For long positions: SL below entry, TP above entry
                sl_price = current_price * (1 - risk_params.get('stop_loss_pct', 0.02))
                tp_price = current_price * (1 + risk_params.get('take_profit_pct', 0.03))
            else:  # SELL
                # For short positions: SL above entry, TP below entry
                sl_price = current_price * (1 + risk_params.get('stop_loss_pct', 0.02))  # SL above for SELL
                tp_price = current_price * (1 - risk_params.get('take_profit_pct', 0.03))  # TP below for SELL

            # Create order with risk parameters from the execution intent (set by Strategy layer)
            # The Strategy layer should have already calculated all risk parameters
            order = Order(
                symbol=execution_intent.symbol,
                side=order_side,
                order_type="MARKET",  # Using string instead of enum
                quantity=Decimal(str(quantity)),
                price=Money(amount=float(current_price), currency='USDT') if current_price else None,
                strategy_name=execution_intent.strategy_name,  # Strategy name comes from intent
                timestamp=execution_intent.timestamp,
                position_side=position_side,  # Add position side for futures trading
                stop_loss_price=getattr(execution_intent, 'stop_loss_price', None),  # SL from strategy
                take_profit_price=getattr(execution_intent, 'take_profit_price', None),  # TP from strategy
                parent_execution_intent=execution_intent  # Link back to the execution intent
            )

            # Execute order through execution service
            if hasattr(execution_service_to_use, 'execute_order'):
                try:
                    order_id = execution_service_to_use.execute_order(order)
                    if self.logger:
                        self.logger.info(f"Executed order with ID: {order_id}")
                    return order_id
                except ValueError as ve:
                    if "DUPLICATE:" in str(ve):
                        # Handle duplicate prevention gracefully
                        if self.logger:
                            self.logger.info(f"Duplicate trade prevented: {ve}")
                        return None  # Return None to indicate the trade was prevented
                    else:
                        # Re-raise other ValueErrors
                        if self.logger:
                            self.logger.error(f"Non-duplicate ValueError occurred: {ve}")
                        raise
                except Exception as e:
                    # Handle any other exceptions that might occur
                    if self.logger:
                        self.logger.error(f"Unexpected error during order execution: {e}")
                    return None  # Return None to prevent system crashes
            else:
                if self.logger:
                    self.logger.error("Execution service does not have execute_order method")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing execution intent: {e}")
            import traceback
            if self.logger:
                self.logger.error(f"Traceback: {traceback.format_exc()}")


# Global event router instance
event_router = EventRouter()
signal_processor = SignalProcessor(event_router)

# Start the event router
event_router.start()