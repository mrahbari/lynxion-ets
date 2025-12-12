"""
Workflow orchestrator for the complete trading workflow: Watcher → Engine → Fusion → Strategy → Broker
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
from domain.entities.trading_entities import Signal, Order
from domain.value_objects import Symbol
from domain.ports.watcher_ports import WatcherPort
from domain.ports.engine_ports import EnginePort, StrategyPort
from domain.ports.trading_ports import OrderManagementPort
from domain.ports.execution_ports import ExecutionPort
from shared.logger import logger


class WorkflowOrchestrator:
    """Coordinates the complete trading workflow: Watcher → Engine → Fusion → Strategy → Broker"""

    def __init__(self,
                 watchers: List[WatcherPort],
                 engines: List[EnginePort],
                 strategy: StrategyPort,
                 fusion_port,
                 order_management_port: OrderManagementPort,
                 execution_port: ExecutionPort,
                 risk_service=None):
        """
        Initialize the workflow orchestrator with all necessary components
        
        Args:
            watchers: List of market watchers
            engines: List of signal processing engines  
            strategy: Trading strategy
            fusion_port: Signal fusion component
            order_management_port: Order management component
            execution_port: Execution component
            risk_service: Optional risk management service
        """
        self.watchers = watchers
        self.engines = engines
        self.strategy = strategy
        self.fusion_port = fusion_port
        self.order_management = order_management_port
        self.execution = execution_port
        self.risk_service = risk_service

    def execute_complete_workflow(self, symbol: Symbol, market_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Execute the complete workflow: Watcher → Engine → Fusion → Strategy → Broker
        
        Args:
            symbol: Trading symbol to process
            market_data: Optional market data to use
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            # Step 1: Watcher analysis
            raw_signals = self._execute_watcher_phase(symbol)
            if not raw_signals:
                logger.info(f"No signals generated from watchers for {symbol.value}")
                return None

            # Step 2: Engine processing
            processed_signals = self._execute_engine_phase(raw_signals)
            if not processed_signals:
                logger.info(f"No signals passed engine processing for {symbol.value}")
                return None

            # Step 3: Fusion (if multiple signals)
            if len(processed_signals) > 1:
                fused_signal = self._execute_fusion_phase(processed_signals)
                if not fused_signal:
                    logger.info(f"Fusion failed for {symbol.value}")
                    return None
                final_signal = fused_signal
            else:
                final_signal = processed_signals[0]

            # Step 4: Strategy application
            strategy_signal = self._execute_strategy_phase(symbol, final_signal)
            if not strategy_signal:
                logger.info(f"Strategy rejected signal for {symbol.value}")
                return None

            # Step 5: Risk validation
            if self.risk_service:
                is_valid = self.risk_service.validate_trade(strategy_signal)
                if not is_valid:
                    logger.info(f"Risk validation failed for {symbol.value}")
                    return None

            # Step 6: Order execution
            order_id = self._execute_execution_phase(strategy_signal)
            if not order_id:
                logger.info(f"Order execution failed for {symbol.value}")
                return None

            logger.info(f"Complete workflow executed successfully for {symbol.value}, order ID: {order_id}")
            return order_id

        except Exception as e:
            logger.error(f"Error in complete workflow execution for {symbol.value}: {e}")
            return None

    def _execute_watcher_phase(self, symbol: Symbol) -> List[Signal]:
        """Execute the watcher phase to generate raw signals"""
        try:
            raw_signals = []
            
            for watcher in self.watchers:
                if not watcher.is_running():
                    logger.debug(f"Starting watcher {watcher.__class__.__name__}")
                    watcher.start()
                
                # Update watcher with any available market data
                # This could be extended to pass specific data to watchers
                signal = watcher.analyze(symbol)
                if signal:
                    raw_signals.append(signal)
                    logger.debug(f"Watcher {watcher.__class__.__name__} generated signal: {signal.signal_type.name}")

            logger.info(f"Watcher phase completed: {len(raw_signals)} signals generated for {symbol.value}")
            return raw_signals
            
        except Exception as e:
            logger.error(f"Error in watcher phase for {symbol.value}: {e}")
            return []

    def _execute_engine_phase(self, signals: List[Signal]) -> List[Signal]:
        """Execute the engine phase to process signals through all engines"""
        try:
            processed_signals = []
            
            for signal in signals:
                # Process through all engines
                processed_signal = signal
                for engine in self.engines:
                    if engine.should_process_signal(processed_signal):
                        try:
                            processed_signal = engine.process_signal(processed_signal)
                            logger.debug(f"Engine {engine.get_engine_name()} processed signal")
                        except Exception as e:
                            logger.warning(f"Engine {engine.get_engine_name()} failed to process signal: {e}")
                            # Continue with original signal if engine fails
                            continue
                
                processed_signals.append(processed_signal)

            logger.info(f"Engine phase completed: {len(processed_signals)} signals processed")
            return processed_signals
            
        except Exception as e:
            logger.error(f"Error in engine phase: {e}")
            return []

    def _execute_fusion_phase(self, signals: List[Signal]) -> Optional[Signal]:
        """Execute the fusion phase to combine multiple signals into one"""
        try:
            if not signals:
                return None
            
            # Use the fusion port to combine signals
            fused_signal = self.fusion_port.fuse_signals(signals)
            logger.info(f"Fusion phase completed: {len(signals)} signals fused into 1")
            return fused_signal
            
        except Exception as e:
            logger.error(f"Error in fusion phase: {e}")
            return None

    def _execute_strategy_phase(self, symbol: Symbol, signal: Signal) -> Optional[Signal]:
        """Execute the strategy phase to apply strategy-specific logic"""
        try:
            # The strategy can either generate a new signal based on the input
            # or return the same signal with potentially modified values
            strategy_signal = self.strategy.generate_signal(symbol)
            
            if strategy_signal:
                logger.info(f"Strategy phase completed for {symbol.value}")
                return strategy_signal
            else:
                # If strategy doesn't generate its own signal, return the input signal
                logger.info(f"Using input signal in strategy phase for {symbol.value}")
                return signal
                
        except Exception as e:
            logger.error(f"Error in strategy phase for {symbol.value}: {e}")
            return None

    def _execute_execution_phase(self, signal: Signal) -> Optional[str]:
        """Execute the order execution phase"""
        try:
            # Create an order from the signal
            order = self._create_order_from_signal(signal)
            if not order:
                logger.warning("Failed to create order from signal")
                return None

            # Place the order
            order_id = self.order_management.place_order(order)
            if order_id:
                logger.info(f"Order execution phase completed, order ID: {order_id}")
                return order_id
            else:
                logger.warning("Order management failed to place order")
                return None

        except Exception as e:
            logger.error(f"Error in execution phase: {e}")
            return None

    def _create_order_from_signal(self, signal: Signal) -> Optional[Order]:
        """Create an order from a trading signal"""
        try:
            from domain.entities.trading_entities import Order
            from domain.value_objects import Money
            
            # Determine order side based on signal type
            side = "BUY" if signal.signal_type.name == "BUY" else "SELL"
            
            # Calculate position size (this would be more sophisticated in a real implementation)
            # For now, use a simple sizing based on confidence
            confidence_factor = float(signal.confidence.value)
            base_quantity = 0.01  # Base quantity
            quantity = base_quantity * (0.5 + confidence_factor * 0.5)  # Range 0.5% to 1% based on confidence

            # Create the order
            order = Order(
                symbol=signal.symbol,
                side=side,
                quantity=quantity,
                price=None,  # Market order
                order_type="MARKET",
                strategy=signal.strategy_name,
                timestamp=datetime.now(),
                metadata=signal.metadata
            )

            return order

        except Exception as e:
            logger.error(f"Error creating order from signal: {e}")
            return None

    def execute_batch_workflow(self, symbols: List[Symbol], 
                              market_data: Optional[Dict[Symbol, Dict[str, Any]]] = None) -> Dict[str, Optional[str]]:
        """
        Execute the complete workflow for multiple symbols
        
        Args:
            symbols: List of symbols to process
            market_data: Optional market data dictionary keyed by Symbol
            
        Returns:
            Dictionary mapping symbol to order ID (or None if failed)
        """
        results = {}
        
        for symbol in symbols:
            market_data_for_symbol = market_data.get(symbol) if market_data else None
            order_id = self.execute_complete_workflow(symbol, market_data_for_symbol)
            results[symbol.value] = order_id
            
            # Small delay between processing symbols to avoid overwhelming systems
            time.sleep(0.1)
        
        logger.info(f"Batch workflow completed for {len(symbols)} symbols")
        return results

    def update_all_components_with_market_data(self, market_data: Dict[str, Any]):
        """Update all workflow components with market data"""
        # Update watchers
        for watcher in self.watchers:
            try:
                watcher.update_data(market_data)
            except Exception as e:
                logger.warning(f"Error updating watcher with market data: {e}")
        
        # Update engines
        for engine in self.engines:
            try:
                engine.update_with_market_data(market_data)
            except Exception as e:
                logger.warning(f"Error updating engine with market data: {e}")
                
        # Update strategy if it has update method
        if hasattr(self.strategy, 'update_with_market_data'):
            try:
                self.strategy.update_with_market_data(market_data)
            except Exception as e:
                logger.warning(f"Error updating strategy with market data: {e}")

    def get_workflow_status(self) -> Dict[str, Any]:
        """Get the current status of the workflow components"""
        return {
            'watchers_count': len(self.watchers),
            'engines_count': len(self.engines),
            'strategy': self.strategy.__class__.__name__,
            'active_watchers': sum(1 for w in self.watchers if w.is_running()),
            'last_execution_time': datetime.now().isoformat(),
            'components': {
                'watchers': [w.__class__.__name__ for w in self.watchers],
                'engines': [e.get_engine_name() for e in self.engines],
                'strategy': self.strategy.__class__.__name__
            }
        }