"""
Engine port adapter to connect EngineManagementService to SignalProcessingService.
"""
from domain.entities.trading_entities import Signal
from domain.ports.engine_ports import EnginePort
from typing import List, Optional
from application.services.engine_services import EngineManagementService


class EngineManagementToEnginePortAdapter(EnginePort):
    """Adapter to make EngineManagementService compatible with EnginePort"""
    
    def __init__(self, engine_management_service: EngineManagementService):
        self.engine_management_service = engine_management_service
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process signal by routing through all engines using the engine management service"""
        return self.engine_management_service.process_signal_through_all_engines(signal)
    
    def should_process_signal(self, signal: Signal) -> bool:
        """Check if the engines should process this signal"""
        # For the adapter, we'll assume all signals are processed by the service
        return True
    
    def get_engine_name(self) -> str:
        """Get the engine name"""
        return "EngineManagementAdapter"