"""
Signal port adapter to connect strategy selection to signal processing.
"""
from domain.entities.trading_entities import Signal
from domain.value_objects import Symbol
from domain.ports.trading_ports import SignalPort
from typing import Optional
from application.services.strategy_services import StrategySelectionService


class StrategyToSignalPortAdapter(SignalPort):
    """Adapter to make StrategySelectionService compatible with SignalPort"""
    
    def __init__(self, strategy_selection_service: StrategySelectionService):
        self.strategy_selection_service = strategy_selection_service
    
    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal by delegating to strategy selection"""
        return self.strategy_selection_service.generate_signal_with_optimal_strategy(symbol)
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal - this would typically be handled by engine ports"""
        # This method may not be directly applicable in this context
        # since StrategySelectionService doesn't process signals, it generates them
        # For now, return the signal as is
        return signal