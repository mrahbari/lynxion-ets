"""
Event system for proper signal routing between architectural layers.
Following correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
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
                self.logger.info(f"Processing fused signal from {event.source_component} for {fused_signal.symbol.value}")
            
            # Process signal through strategy manager
            execution_intent = strategy_manager.evaluate_fused_signal(fused_signal)
            
            if execution_intent:
                # Publish execution intent for final layer
                self.event_router.publish_execution_intent(
                    execution_intent,
                    source="StrategyManager",
                    correlation_id=event.correlation_id
                )
                if self.logger:
                    self.logger.info(f"Published execution intent: {execution_intent.side.name} for {execution_intent.symbol.value}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing fused signal: {e}")

    def _process_execution_intent(self, event: SignalEvent, execution_service):
        """Process execution intent through broker layer"""
        try:
            execution_intent = event.data
            if self.logger:
                self.logger.info(f"Processing execution intent from {event.source_component} for {execution_intent.symbol.value}")
            
            # Execute the trade through the execution service
            # This would need to be implemented based on the execution service interface
            if hasattr(execution_service, 'execute_intent_trade'):
                order_id = execution_service.execute_intent_trade(execution_intent)
                if self.logger:
                    self.logger.info(f"Executed trade with ID: {order_id}")
            else:
                # Fallback implementation - need to create order from intent and execute
                from domain.entities.signal_entities import Order, OrderSide
                from domain.value_objects import Money
                from decimal import Decimal
                
                # Create order from execution intent
                order = Order(
                    symbol=execution_intent.symbol,
                    side=execution_intent.side,
                    quantity=Decimal('0.001'),  # Default small quantity for testing
                    price=Money(amount=0, currency='USDT'),  # Will be set by market price
                    strategy_name=execution_intent.strategy_name,
                    risk_parameters=execution_intent.risk_parameters
                )
                
                # Execute order through execution service
                if hasattr(execution_service, 'execute_order'):
                    order_id = execution_service.execute_order(order)
                    if self.logger:
                        self.logger.info(f"Executed order with ID: {order_id}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing execution intent: {e}")


# Global event router instance
event_router = EventRouter()
signal_processor = SignalProcessor(event_router)

# Start the event router
event_router.start()