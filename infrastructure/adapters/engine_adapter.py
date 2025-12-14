"""
Engine port adapter that implements EnginePort using a collection of engines.
This adapter follows hexagonal architecture by only depending on domain interfaces,
not directly on application services.
"""
from domain.entities.trading_entities import Signal
from domain.ports.engine_ports import EnginePort
from domain.ports.engine_ports import EnginePort as DomainEnginePort
from typing import List, Optional


class EngineCollectionAdapter(EnginePort):
    """Adapter that implements EnginePort by managing a collection of engine implementations"""

    def __init__(self, engines: List[DomainEnginePort]):
        self.engines = engines

    def process_signal(self, signal: Signal) -> Signal:
        """Process signal by routing through all registered engines"""
        processed_signal = signal
        for engine in self.engines:
            if engine.should_process_signal(processed_signal):
                processed_signal = engine.process_signal(processed_signal)
        return processed_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if any engine should process this signal"""
        return any(engine.should_process_signal(signal) for engine in self.engines)

    def update_with_market_data(self, data):
        """Update all engines with market data"""
        for engine in self.engines:
            engine.update_with_market_data(data)

    def get_engine_name(self) -> str:
        """Get the engine name"""
        return "EngineCollectionAdapter"