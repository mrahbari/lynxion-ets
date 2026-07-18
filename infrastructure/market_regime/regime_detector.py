"""
Market regime detection system to classify current market conditions
and adjust trading strategies accordingly. Delegated to the 4H Macro Regime Engine.
"""
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

from infrastructure.market_regime._regime_classifiers import RegimeType
from infrastructure.market_regime.macro_regime_engine import MacroRegimeEngine


class RegimeDetector:
    """Detects current market regime based on price/volume data using the 4H Macro Regime Engine."""

    def __init__(self, lookback_period: int = 50, volatility_window: int = 20,
                 confidence_threshold: float = 0.6, decay_factor: float = 0.95):
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        self.confidence_threshold = confidence_threshold
        self.decay_factor = decay_factor

        # Delegate to the unified MacroRegimeEngine
        self.engine = MacroRegimeEngine(
            lookback_period=lookback_period,
            volatility_window=volatility_window,
            confidence_threshold=confidence_threshold
        )

    def detect_regime(self, prices: List[float], volumes: List[float] = None) -> Dict:
        """Detect the current market regime with confidence scoring."""
        return self.engine.detect_regime_from_series(prices, volumes)


# Module-level singleton lazy accessor for backward compatibility
_regime_detector_singleton = None


def __getattr__(name):
    global _regime_detector_singleton
    if name == "regime_detector":
        if _regime_detector_singleton is None:
            _regime_detector_singleton = RegimeDetector()
        return _regime_detector_singleton
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")