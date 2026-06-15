"""
Use cases for engine functionality in the enterprise hedge fund trading system.
"""
from domain.entities import Signal
from application.services.engine_services import EngineOrchestrationService


class ProcessSignalThroughEnginesUseCase:
    """Use case for processing a signal through all applicable engines"""
    
    def __init__(self, engine_orchestration_service: EngineOrchestrationService):
        self.engine_orchestration_service = engine_orchestration_service
    
    def execute(self, signal: Signal) -> Signal:
        """Execute the use case to process a signal through all engines"""
        return self.engine_orchestration_service.orchestrate_signal_processing(signal)


class GetEngineStatusUseCase:
    """Use case for getting the status of all engines"""
    
    def __init__(self, engine_service):
        self.engine_service = engine_service
    
    def execute(self) -> list:
        """Execute the use case to get engine statuses"""
        return self.engine_service.get_engine_status()