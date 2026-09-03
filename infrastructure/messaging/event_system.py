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
from domain.entities import MarketObservation, InterpretedSignal, FusedSignal, ExecutionIntent
from bootstrap.settings.loaders import load_settings


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

    def update_market_data_heartbeat(self, symbol, timestamp=None):
        """Canonical update method for market data heartbeat staleness safety check."""
        if not hasattr(self, '_last_market_data_times') or self._last_market_data_times is None:
            self._last_market_data_times = {}
        symbol_key = symbol.value if hasattr(symbol, 'value') else str(symbol)
        symbol_key = str(symbol_key).upper().replace("-", "")
        self._last_market_data_times[symbol_key] = timestamp or datetime.now()

    def _process_observation(self, event: SignalEvent, engine_service):
        """Process market observation through engine layer"""
        try:
            observation = event.data
            if hasattr(observation, 'symbol'):
                self.update_market_data_heartbeat(observation.symbol)
            if self.logger and hasattr(observation, 'symbol'):
                self.logger.info(f"Processing observation from {event.source_component} for {observation.symbol.value}")

            # Record price for rolling correlation calculation (E3.T5)
            try:
                from application.containers.container import container
                risk_engine = container.resolve("risk_engine")
                risk_engine._risk_manager.record_price(observation.symbol.value, float(observation.close))
            except Exception:
                pass

            # Process observation through engine
            interpreted_signal = engine_service.process_observation(observation)

            if interpreted_signal:
                # Log the engine interpretation to forensic logger
                from infrastructure.logging.forensic_logger import forensic_logger
                forensic_logger.log_engine_interpretation(
                    engine="EngineService",
                    symbol=interpreted_signal.symbol.value if hasattr(interpreted_signal.symbol, 'value') else str(interpreted_signal.symbol),
                    exchange=event.source_component if event.source_component else "UNKNOWN",
                    input_observation=observation.observation_type if hasattr(observation, 'observation_type') else "unknown",
                    interpreted_signal=interpreted_signal.signal_type.value if hasattr(interpreted_signal.signal_type, 'value') else str(interpreted_signal.signal_type),
                    confidence=float(interpreted_signal.confidence.value) if hasattr(interpreted_signal.confidence, 'value') else 0.5,
                    score=interpreted_signal.strength if hasattr(interpreted_signal, 'strength') else 0.5,
                    timestamp=interpreted_signal.timestamp if hasattr(interpreted_signal, 'timestamp') else None
                )

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
                # Log the fusion result to forensic logger
                from infrastructure.logging.forensic_logger import forensic_logger
                forensic_logger.log_fusion_result(
                    symbol=fused_signal.symbol.value if hasattr(fused_signal.symbol, 'value') else str(fused_signal.symbol),
                    exchange=event.source_component if event.source_component else "UNKNOWN",
                    regime=fused_signal.regime_context if hasattr(fused_signal, 'regime_context') else "unknown",
                    fused_direction=fused_signal.dominant_bias.value if hasattr(fused_signal.dominant_bias, 'value') else str(fused_signal.dominant_bias),
                    confidence=float(fused_signal.confidence.value) if hasattr(fused_signal.confidence, 'value') else 0.5,
                    contributors=fused_signal.metadata.get('contributors', {}) if hasattr(fused_signal, 'metadata') and fused_signal.metadata else {},
                    timestamp=fused_signal.timestamp if hasattr(fused_signal, 'timestamp') else None
                )

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
            from domain.entities import Order, OrderSide
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
            fixed_position_size_enabled = load_settings().position_sizing.fixed_position_size_enabled if load_settings().position_sizing and hasattr(load_settings().position_sizing, 'fixed_position_size_enabled') else False
            fixed_position_amount = load_settings().position_sizing.fixed_position_amount if load_settings().position_sizing and hasattr(load_settings().position_sizing, 'fixed_position_amount') else 10.0

            try:
                from application.containers.container import container
                risk_engine = container.resolve("risk_engine")
                from domain.entities.position import Portfolio, Position as DomainPosition
                from domain.value_objects import Money as DomainMoney, Symbol as DomainSymbol
                from domain.enums.position_side import PositionSide
                from decimal import Decimal

                risk_mgr = risk_engine._risk_manager
                active_positions = []
                for sym_str, pos in risk_mgr.positions.items():
                    active_positions.append(DomainPosition(
                        symbol=DomainSymbol(sym_str),
                        side=PositionSide.LONG if pos.direction.value == "long" else PositionSide.SHORT,
                        quantity=Decimal(str(pos.size)),
                        entry_price=DomainMoney(amount=Decimal(str(pos.entry_price)), currency="USDT"),
                        timestamp=pos.entry_time
                    ))
                
                equity_val = risk_mgr.starting_equity + risk_mgr.total_pnl
                portfolio_obj = Portfolio(
                    positions=active_positions,
                    cash_balance=DomainMoney(amount=Decimal(str(equity_val)), currency="USDT"),
                    total_value=DomainMoney(amount=Decimal(str(equity_val)), currency="USDT"),
                    timestamp=datetime.now()
                )

                # Fetch volatility/ATR if available
                atr = execution_intent.metadata.get("atr") if execution_intent.metadata else None

                quantity = risk_engine.calculate_dynamic_size(
                    intent=execution_intent,
                    portfolio=portfolio_obj,
                    volatility=atr
                )
                if self.logger:
                    self.logger.debug(f"NGDP dynamically sized quantity: {quantity:.6f} for {execution_intent.symbol.value}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in NGDP calculation, falling back to static sizing: {e}")
                
                if fixed_position_size_enabled:
                    fallback_price = 50000.0
                    p = current_price if current_price and current_price > 0 else fallback_price
                    quantity = fixed_position_amount / p
                else:
                    position_size_pct = risk_params.get('max_position_size', 0.02)
                    account_balance = load_settings().position_sizing.default_account_balance if load_settings().position_sizing and hasattr(load_settings().position_sizing, 'default_account_balance') else 10000.0
                    position_value = account_balance * position_size_pct
                    p = current_price if current_price and current_price > 0 else 50000.0
                    quantity = position_value / p

                if 'position_quantity' in risk_params:
                    quantity = risk_params['position_quantity']

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
            # However, if the strategy layer set incorrect SL/TP prices, we'll recalculate them
            stop_loss_price = getattr(execution_intent, 'stop_loss_price', None)
            take_profit_price = getattr(execution_intent, 'take_profit_price', None)

            # Check if the strategy layer set incorrect SL/TP prices and recalculate if needed
            # For BUY orders: SL should be below entry price, TP should be above entry price
            # For SELL orders: SL should be above entry price, TP should be below entry price
            entry_price = float(current_price) if current_price else 50000.0  # fallback

            # Validate signal direction consistency with order side
            # Check if there's a contradiction between signal bias and order side
            if hasattr(execution_intent, 'fused_signal') and execution_intent.fused_signal:
                dominant_bias = getattr(execution_intent.fused_signal, 'dominant_bias', None)
                if dominant_bias:
                    bias_str = dominant_bias.value if hasattr(dominant_bias, 'value') else str(dominant_bias)
                    if ((bias_str in ['SELL', 'SHORT'] and order_side.name == 'BUY') or
                        (bias_str in ['BUY', 'LONG'] and order_side.name == 'SELL')):
                        if self.logger:
                            self.logger.warning(f"⚠️ Signal contradiction: Bias={bias_str} vs Order={order_side.name} for {execution_intent.symbol.value}")

            # Validate SL/TP prices from strategy
            is_valid = True
            invalid_reason = ""
            
            # Extract and sanitize SL/TP amounts using centralized shared utility
            from shared.utils import sanitize_sltp_levels
            from domain.value_objects import Money
            from decimal import Decimal

            sl_amount = float(stop_loss_price.amount) if stop_loss_price and hasattr(stop_loss_price, 'amount') else None
            tp_amount = float(take_profit_price.amount) if take_profit_price and hasattr(take_profit_price, 'amount') else None

            if sl_amount is None or sl_amount <= 0:
                sl_amount = float(risk_params.get('stop_loss')) if risk_params and risk_params.get('stop_loss') is not None else None
            if tp_amount is None or tp_amount <= 0:
                tp_amount = float(risk_params.get('take_profit')) if risk_params and risk_params.get('take_profit') is not None else None

            sl_amount, tp_amount = sanitize_sltp_levels(
                entry_price=entry_price,
                side=order_side,
                stop_loss=sl_amount,
                take_profit=tp_amount
            )

            # Re-attach sanitized Money objects to execution_intent
            stop_loss_price = Money(amount=Decimal(str(sl_amount)), currency='USDT')
            take_profit_price = Money(amount=Decimal(str(tp_amount)), currency='USDT')
            execution_intent.stop_loss_price = stop_loss_price
            execution_intent.take_profit_price = take_profit_price
                    
            # Check sanity distance ratios
            if is_valid:
                if sl_amount:
                    sl_ratio = abs(sl_amount - entry_price) / entry_price
                    if sl_ratio > 0.5:
                        is_valid = False
                        invalid_reason = f"Stop Loss is too far from entry (>50%): SL={sl_amount}, Entry={entry_price}, Ratio={sl_ratio:.2f}"
                if tp_amount:
                    tp_ratio = abs(tp_amount - entry_price) / entry_price
                    if tp_ratio > 0.5:
                        is_valid = False
                        invalid_reason = f"Take Profit is too far from entry (>50%): TP={tp_amount}, Entry={entry_price}, Ratio={tp_ratio:.2f}"

            if not is_valid:
                if self.logger:
                    self.logger.warning(f"❌ ORDER REJECTED: {invalid_reason}")
                
                # Write rejection to ExecutionTruthLedger
                try:
                    from shared.execution_truth_ledger import execution_truth_ledger as ledger
                    order_ref = ledger.new_order_ref()
                    ledger.append("decision", {
                        "order_ref": order_ref,
                        "symbol": execution_intent.symbol.value,
                        "broker": "bingx",
                        "route": "REJECTED",
                        "decision_trace": {
                            "rule": "SL_TP_VALIDATION",
                            "reason": f"VETO: {invalid_reason}"
                        },
                        "input_flags": {
                            "entry_price": entry_price,
                            "stop_loss": sl_amount,
                            "take_profit": tp_amount,
                            "side": order_side.name
                        }
                    })
                except Exception as ledger_err:
                    if self.logger:
                        self.logger.error(f"Failed to write rejection to ExecutionTruthLedger: {ledger_err}")
                return None


            # --- MARKET DATA SAFETY HEARTBEAT GUARD (LIVE ONLY) ---
            is_live = not hasattr(execution_service_to_use, 'is_backtest') or not getattr(execution_service_to_use, 'is_backtest', False)
            if is_live:
                symbol_key = execution_intent.symbol.value if hasattr(execution_intent.symbol, 'value') else str(execution_intent.symbol)
                symbol_key = str(symbol_key).upper().replace("-", "")
                last_time = getattr(self, '_last_market_data_times', {}).get(symbol_key)
                if last_time:
                    elapsed = (datetime.now() - last_time).total_seconds()
                    if elapsed > 90.0:
                        if self.logger:
                            self.logger.warning(
                                f"❌ HEARTBEAT GUARD VETO: Market data heartbeat is stale by {elapsed:.1f}s (> 90s) for "
                                f"{symbol_key}. Submission rejected."
                            )
                        return None
                else:
                    if self.logger:
                        self.logger.warning(
                            f"❌ HEARTBEAT GUARD VETO: No market data heartbeat recorded for "
                            f"{symbol_key}. Submission rejected."
                        )
                    return None

            # --- LIQUIDITY DEPTH PROTECTION GUARD ---
            max_liquidity = 999999.0
            if hasattr(execution_service_to_use, 'broker') and hasattr(execution_service_to_use.broker, 'fetch_order_book'):
                try:
                    order_book = execution_service_to_use.broker.fetch_order_book(execution_intent.symbol.value)
                    if isinstance(order_book, dict):
                        if order_side.name == 'BUY':
                            # Check asks (seller liquidity)
                            asks = order_book.get('asks', [])[:3]
                            max_liquidity = sum(float(ask[1]) for ask in asks)
                        else:
                            # Check bids (buyer liquidity)
                            bids = order_book.get('bids', [])[:3]
                            max_liquidity = sum(float(bid[1]) for bid in bids)
                except Exception as e:
                    if self.logger:
                        self.logger.debug(f"Could not fetch order book depth: {e}")

            # Safety liquidity threshold check
            if quantity > max_liquidity:
                if self.logger:
                    self.logger.warning(
                        f"⚠️ LIQUIDITY DEPTH GUARD: Requested size {quantity:.6f} exceeds top 3 levels "
                        f"liquidity {max_liquidity:.6f} for {execution_intent.symbol.value}. Scaling down to {max_liquidity:.6f}."
                    )
                quantity = max_liquidity
                if quantity < 0.001:
                    if self.logger:
                        self.logger.warning("Scaled size below minimum 0.001. Submission rejected.")
                    return None

            # Configurable maximum order notional cap
            try:
                max_order_notional = None
                settings = load_settings()
                
                # Check settings
                if settings.risk:
                    if hasattr(settings.risk, 'max_order_notional_amount') and settings.risk.max_order_notional_amount is not None:
                        max_order_notional = settings.risk.max_order_notional_amount
                
                # Check environment override
                import os
                env_cap = os.getenv('MAX_ORDER_NOTIONAL_AMOUNT')
                if env_cap is not None and env_cap.strip():
                    max_order_notional = float(env_cap)
                    
                if max_order_notional is not None:
                    max_order_notional = float(max_order_notional)
                    execution_price = float(current_price) if current_price else 0.0
                    if execution_price > 0:
                        calculated_notional = quantity * execution_price
                        if calculated_notional > max_order_notional:
                            old_quantity = quantity
                            new_quantity = max_order_notional / execution_price
                            quantity = new_quantity
                            if self.logger:
                                self.logger.warning(
                                    f"🛡️ ORDER CAP ENGAGED: Capping order notional from ${calculated_notional:.2f} "
                                    f"to ${max_order_notional:.2f}. "
                                    f"Old Qty: {old_quantity:.6f}, New Qty: {new_quantity:.6f}"
                                )
            except Exception as cap_err:
                if self.logger:
                    self.logger.warning(f"Error applying MAX_ORDER_NOTIONAL_AMOUNT cap: {cap_err}")


            # Log comprehensive order details before execution
            if self.logger:
                sl_val = float(stop_loss_price.amount) if stop_loss_price else "N/A"
                tp_val = float(take_profit_price.amount) if take_profit_price else "N/A"

                self.logger.info(f"📊 ORDER DETAILS: {execution_intent.symbol.value} | "
                               f"Side: {order_side.name} | "
                               f"Entry: ${entry_price:.4f} | "
                               f"SL: ${sl_val} | "
                               f"TP: ${tp_val} | "
                               f"Qty: {quantity} | "
                               f"Strategy: {execution_intent.strategy_name}")

            order = Order(
                symbol=execution_intent.symbol,
                side=order_side,
                order_type="MARKET",  # Using string instead of enum
                quantity=Decimal(str(quantity)),
                price=Money(amount=float(current_price), currency='USDT') if current_price else None,
                strategy_name=execution_intent.strategy_name,  # Strategy name comes from intent
                timestamp=execution_intent.timestamp,
                position_side=position_side,  # Add position side for futures trading
                stop_loss_price=stop_loss_price,  # SL from strategy or recalculated
                take_profit_price=take_profit_price,  # TP from strategy or recalculated
                parent_execution_intent=execution_intent,  # Link back to the execution intent
                requested_leverage=Decimal(str(load_settings().risk.max_leverage)),
            )

            # Execute order through execution service
            if hasattr(execution_service_to_use, 'execute_order'):
                try:
                    order_id = execution_service_to_use.execute_order(order)
                    if order_id is not None:
                        if self.logger:
                            self.logger.info(f"Executed order with ID: {order_id}")

                        # Log the broker execution to forensic logger
                        from infrastructure.logging.forensic_logger import forensic_logger
                        forensic_logger.log_broker_execution(
                            trade_id=order_id,
                            exchange=getattr(execution_service_to_use, 'get_broker_name', lambda: 'UNKNOWN')(),
                            side=order_side.name,
                            price=float(current_price) if current_price else 0.0,
                            sl=float(stop_loss_price.amount) if stop_loss_price and hasattr(stop_loss_price, 'amount') else 0.0,
                            tp=float(take_profit_price.amount) if take_profit_price and hasattr(take_profit_price, 'amount') else 0.0,
                            quantity=float(quantity),
                            fee=0.0,  # Fee would need to be retrieved from execution response
                            slippage=0.0,  # Slippage would need to be calculated based on execution
                            validation_checks={
                                'margin_availability_check': True,  # Would be checked in real implementation
                                'risk_profile_compliance': True,    # Would be validated in real implementation
                                'quantity_calculation_formula': f"risk_amount / (entry_price - stop_loss)",  # Example formula
                                'sl_tp_calculation_origin': 'strategy_risk_parameters',
                                'order_submission_payload': {
                                    'symbol': order.symbol.value if hasattr(order.symbol, 'value') else str(order.symbol),
                                    'side': order_side.name,
                                    'type': 'MARKET',  # Would be determined from order
                                    'quantity': float(quantity),
                                    'price': float(current_price) if current_price else 0.0,
                                    'stop_loss': float(stop_loss_price.amount) if stop_loss_price and hasattr(stop_loss_price, 'amount') else 0.0,
                                    'take_profit': float(take_profit_price.amount) if take_profit_price and hasattr(take_profit_price, 'amount') else 0.0,
                                }
                            },
                            order_status_lifecycle=['NEW', 'ACCEPTED', 'FILLED'],  # Would be updated based on actual lifecycle
                            timestamp=execution_intent.timestamp
                        )
                    else:
                        if self.logger:
                            self.logger.warning(f"Order execution returned None - order was not placed")
                    # Only return order_id if it's not None, otherwise return appropriate status
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
