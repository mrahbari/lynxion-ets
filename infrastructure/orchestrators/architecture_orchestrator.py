"""
Architecture Orchestrator for proper signal flow between layers.
Following correct architecture: Watcher → Engine → Fusion → Strategy → Broker
"""
import threading
import time
from typing import Dict, Any, Optional
from domain.entities.signal_entities import MarketObservation, InterpretedSignal, FusedSignal, ExecutionIntent
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from shared.event_system import event_router, signal_processor
from infrastructure.engines.engine_service import engine_service
from infrastructure.fusion.fusion_service import fusion_service
from infrastructure.strategies.strategy_manager import strategy_manager


class ArchitectureOrchestrator:
    """Orchestrates the proper flow between architectural layers using event system."""

    def __init__(self,
                 engine_service=None,
                 fusion_service=None,
                 strategy_manager=None,
                 execution_service=None,
                 event_router=None):
        self.engine_service = engine_service or globals().get('engine_service')
        self.fusion_service = fusion_service or globals().get('fusion_service')
        self.strategy_manager = strategy_manager or globals().get('strategy_manager')
        self.execution_service = execution_service
        self.event_router = event_router or globals().get('event_router')

        self.logger = EnhancedLogger("ArchitectureOrchestrator")
        self.is_running = False
        self.orchestration_thread = None

        # Initialize the signal processor with the services
        signal_processor.logger = self.logger
        signal_processor.setup_signal_processing(
            self.engine_service,
            self.fusion_service,
            self.strategy_manager,
            self.execution_service
        )

    def start(self):
        """Start the architecture orchestrator."""
        if not self.is_running:
            self.is_running = True

            # Subscribe to events and set up the proper processing chain
            self.logger.info("Starting Architecture Orchestrator...")

            # The signal processor is already set up to handle the flow
            # Watcher emits -> Event Router -> Signal Processor -> Proper Layer Processing

            self.logger.info("Architecture Orchestrator started successfully")
            self.logger.info("Proper flow established: Watcher → Engine → Fusion → Strategy → Broker")

    def stop(self):
        """Stop the architecture orchestrator."""
        self.is_running = False
        self.logger.info("Architecture Orchestrator stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            'is_running': self.is_running,
            'engine_service': self.engine_service is not None,
            'fusion_service': self.fusion_service is not None,
            'strategy_manager': self.strategy_manager is not None,
            'execution_service': self.execution_service is not None,
            'event_router': self.event_router is not None,
            'timestamp': time.time()
        }


# Global orchestrator instance
architecture_orchestrator = ArchitectureOrchestrator()
