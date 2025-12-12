"""
Hybrid ML fusion service combining traditional and ML-based approaches
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import numpy as np
import statistics

from domain.entities.trading_entities import Signal
from domain.entities.engine_entities import EngineResult
from domain.value_objects import Symbol, Percentage, Money
from domain.ports.engine_ports import FusionPort
from shared.logger import logger

# Import ML fusion service for enhanced capabilities
try:
    from infrastructure.fusion.ml_signal_fusion import MLSignalFusionService, MLFusionMethod
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    MLSignalFusionService = None
    MLFusionMethod = None

from infrastructure.fusion.fusion_service import FusionServiceAdapter


class HybridMLFusionServiceAdapter(FusionServiceAdapter):
    """Hybrid fusion service combining traditional and ML-based approaches"""
    
    def __init__(self, ml_method: str = 'random_forest'):
        super().__init__()
        
        # Initialize ML fusion service if available
        if ML_AVAILABLE:
            ml_enum = {
                'random_forest': MLFusionMethod.RANDOM_FOREST,
                'gradient_boosting': MLFusionMethod.GRADIENT_BOOSTING,
                'logistic_regression': MLFusionMethod.LOGISTIC_REGRESSION,
                'ensemble': MLFusionMethod.ENSEMBLE
            }.get(ml_method, MLFusionMethod.RANDOM_FOREST)
            
            self.ml_fusion_service = MLSignalFusionService(method=ml_enum)
            self.use_ml_fusion = True
        else:
            self.ml_fusion_service = None
            self.use_ml_fusion = False
            logger.warning("ML fusion not available, falling back to traditional fusion")
    
    def fuse_signals(self, signals: List[Signal]) -> Signal:
        """Fuse multiple signals using hybrid approach (traditional + ML)"""
        if not signals:
            logger.warning("No signals to fuse")
            return None

        # Filter out overlapping signals first (using inherited method)
        filtered_signals = self._filter_overlapping_signals(signals)
        
        if not filtered_signals:
            logger.warning("No non-overlapping signals after filtering")
            return None

        if len(filtered_signals) < self.min_signals_for_fusion:
            logger.info(f"Insufficient signals for fusion ({len(filtered_signals)} < {self.min_signals_for_fusion}), "
                        f"returning most confident signal after overlap filtering")
            # If not enough signals after filtering, return the most confident one
            return max(filtered_signals, key=lambda s: float(s.confidence.value))

        logger.info(f"Fusing {len(filtered_signals)} signals after overlap filtering using hybrid approach")

        # Use ML fusion if available and we have enough signals for ML to be beneficial
        if self.use_ml_fusion and len(filtered_signals) >= 2:
            try:
                ml_fused = True
                fused_signal = self.ml_fusion_service.fuse_signals(filtered_signals)
                
                # If ML fusion fails, fall back to traditional fusion
                if fused_signal is None:
                    logger.info("ML fusion failed, using traditional fusion")
                    ml_fused = False
                else:
                    logger.info(f"ML fusion completed: type={fused_signal.signal_type.name}, confidence={fused_signal.confidence}, score={fused_signal.score}")
                    return fused_signal
            except Exception as e:
                logger.error(f"Error in ML fusion: {e}")
                logger.info("Falling back to traditional fusion")
        else:
            ml_fused = False

        # Fall back to traditional fusion
        # Calculate fusion weights
        weights = self.calculate_fusion_weights(filtered_signals)

        # Apply fusion using weighted average
        fused_signal = self._apply_weighted_fusion(filtered_signals, weights)

        logger.info(f"Traditional fusion completed: type={fused_signal.signal_type.name}, confidence={fused_signal.confidence}, score={fused_signal.score}, ml_used={ml_fused if 'ml_fused' in locals() else False}")
        return fused_signal

    def train_ml_models(self, signals: List[Signal], actual_outcome: float):
        """Train ML models with feedback about actual outcomes"""
        if self.use_ml_fusion and self.ml_fusion_service:
            self.ml_fusion_service.train_with_feedback(signals, actual_outcome)

    def get_ml_model_performance(self) -> Dict[str, Any]:
        """Get performance metrics for ML models"""
        if self.use_ml_fusion and self.ml_fusion_service:
            return self.ml_fusion_service.get_model_performance()
        else:
            return {"ml_unavailable": True}