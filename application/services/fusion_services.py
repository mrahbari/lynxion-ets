"""
Application service for signal fusion in the enterprise hedge fund trading system.
"""
from typing import List, Optional
from domain.entities import Signal
from domain.ports.engine_ports import FusionPort
from shared.logger import logger


class FusionService:
    """Application service for signal fusion operations"""
    
    def __init__(self, fusion_port: FusionPort):
        self.fusion_port = fusion_port
    
    def fuse_signals(self, signals: List[Signal]) -> Optional[Signal]:
        """Fuse multiple signals into a single signal"""
        if not signals:
            logger.warning("No signals to fuse")
            return None
        
        logger.info(f"Fusing {len(signals)} signals")
        fused_signal = self.fusion_port.fuse_signals(signals)
        logger.info(f"Signal fusion completed, result type: {fused_signal.signal_type.name if fused_signal else 'None'}")
        
        return fused_signal
    
    def calculate_fusion_weights(self, signals: List[Signal]) -> List[float]:
        """Calculate weights for fusing signals"""
        weights = self.fusion_port.calculate_fusion_weights(signals)
        return [float(w) for w in weights]  # Convert Percentage objects to floats


class AdvancedFusionService:
    """Advanced fusion service with additional features"""
    
    def __init__(self, fusion_service: FusionService):
        self.fusion_service = fusion_service
    
    def adaptive_fusion(self, signals: List[Signal], market_regime: str = "neutral") -> Optional[Signal]:
        """Perform adaptive fusion based on market regime"""
        # In a real implementation, this would use different fusion methods
        # based on the current market regime
        # For now, we'll just call the regular fusion
        logger.info(f"Performing adaptive fusion for regime: {market_regime}")
        return self.fusion_service.fuse_signals(signals)
    
    def confidence_weighted_fusion(self, signals: List[Signal]) -> Optional[Signal]:
        """Perform fusion weighted by signal confidence"""
        # This would implement a specific fusion method that emphasizes
        # higher confidence signals
        return self.fusion_service.fuse_signals(signals)