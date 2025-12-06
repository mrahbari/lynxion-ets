"""
Application service for managing engines in the enterprise hedge fund trading system.
"""
from typing import List, Optional
from domain.ports.strategy_ports import EnginePort
from domain.entities.trading_entities import Signal
from shared.logger import logger


class EngineManagementService:
    """Application service for managing trading engines"""
    
    def __init__(self, engines: List[EnginePort]):
        self.engines = engines
    
    def process_signal_through_all_engines(self, signal: Signal) -> Signal:
        """Process a signal through all registered engines"""
        processed_signal = signal
        engine_names = []
        
        for engine in self.engines:
            try:
                if engine.should_process_signal(processed_signal):
                    processed_signal = engine.process_signal(processed_signal)
                    engine_names.append(engine.get_engine_name())
                    logger.info(f"Signal processed by engine: {engine.get_engine_name()}")
            except Exception as e:
                logger.error(f"Error in engine {engine.get_engine_name()}: {e}")
        
        logger.info(f"Signal processed by engines: {', '.join(engine_names)}")
        return processed_signal
    
    def get_engine_status(self) -> List[dict]:
        """Get status of all engines"""
        status = []
        for engine in self.engines:
            status.append({
                'name': engine.get_engine_name(),
                'can_process_signal': True  # All our engines can process signals in this implementation
            })
        return status


class EngineOrchestrationService:
    """Service for orchestrating engine operations"""
    
    def __init__(self, engine_service: EngineManagementService):
        self.engine_service = engine_service
    
    def orchestrate_signal_processing(self, signal: Signal) -> Signal:
        """Orchestrate the processing of a signal through multiple engines"""
        logger.info(f"Orchestrating signal processing through engines for {signal.symbol.value}")
        
        # Process the signal through all applicable engines
        processed_signal = self.engine_service.process_signal_through_all_engines(signal)
        
        logger.info(f"Engine orchestration completed for {signal.symbol.value}")
        return processed_signal