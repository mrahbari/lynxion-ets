"""
Signal port adapter to connect strategy selection to signal processing.
This adapter follows hexagonal architecture by only depending on domain interfaces,
not directly on application services.
"""
from domain.entities import Signal
from domain.value_objects import Symbol
from domain.ports.trading_ports import SignalPort
from domain.ports.engine_ports import StrategyPort
from typing import Optional, List


class StrategySelectionSignalAdapter(SignalPort):
    """Adapter that implements SignalPort using StrategyPort implementations"""

    def __init__(self, strategies: List[StrategyPort]):
        self.strategies = strategies
        self.selected_strategy = None

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal by selecting the best strategy and using it"""
        if not self.strategies:
            return None

        # For now, use the first strategy - in a real implementation,
        # this would have more sophisticated selection logic that doesn't depend on application services
        best_strategy = self._select_best_strategy(symbol)
        if best_strategy:
            return best_strategy.generate_signal(symbol)

        return None

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal - for now just return as is"""
        return signal

    def _select_best_strategy(self, symbol: Symbol) -> Optional[StrategyPort]:
        """Select best strategy based on simple criteria - no dependency on application services"""
        if not self.strategies:
            return None

        # For now, return the first strategy - in a real system, this would
        # implement strategy selection logic using domain-level information
        # and performance metrics stored at the domain or infrastructure level
        return self.strategies[0]