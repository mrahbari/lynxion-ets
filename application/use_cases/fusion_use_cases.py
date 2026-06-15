"""
Use cases for fusion functionality in the enterprise hedge fund trading system.
"""
from typing import List, Optional
from domain.entities import Signal
from application.services.fusion_services import AdvancedFusionService


class FuseSignalsUseCase:
    """Use case for fusing multiple signals into a single signal"""
    
    def __init__(self, fusion_service: AdvancedFusionService):
        self.fusion_service = fusion_service
    
    def execute(self, signals: List[Signal]) -> Optional[Signal]:
        """Execute the use case to fuse multiple signals"""
        return self.fusion_service.fuse_signals(signals)


class AdaptiveFusionUseCase:
    """Use case for adaptive fusion based on market conditions"""
    
    def __init__(self, fusion_service: AdvancedFusionService):
        self.fusion_service = fusion_service
    
    def execute(self, signals: List[Signal], market_regime: str = "neutral") -> Optional[Signal]:
        """Execute the use case to adaptively fuse signals based on market regime"""
        return self.fusion_service.adaptive_fusion(signals, market_regime)


class ConfidenceWeightedFusionUseCase:
    """Use case for fusing signals weighted by confidence"""
    
    def __init__(self, fusion_service: AdvancedFusionService):
        self.fusion_service = fusion_service
    
    def execute(self, signals: List[Signal]) -> Optional[Signal]:
        """Execute the use case to perform confidence-weighted fusion"""
        return self.fusion_service.confidence_weighted_fusion(signals)