"""4H Macro Regime Engine defining macro volatility and trend states."""

from typing import Dict, List, Any
from infrastructure.market_regime._regime_classifiers import RegimeType, ConfidenceBasedRegimeClassifier, RegimeVetoMechanism


class MacroRegimeEngine:
    """
    Unified 4H Macro Regime Engine.
    Responsible for classifying macro volatility and trend regimes from price series or indicators.
    """

    def __init__(self, lookback_period: int = 50, volatility_window: int = 20,
                 confidence_threshold: float = 0.6):
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        self.confidence_threshold = confidence_threshold

        self.classifier = ConfidenceBasedRegimeClassifier(
            lookback_period=lookback_period,
            volatility_window=volatility_window,
            confidence_threshold=confidence_threshold,
            transition_smoothing_window=3
        )
        self.veto_mechanism = RegimeVetoMechanism()

    def detect_regime_from_series(self, prices: List[float], volumes: List[float] = None) -> Dict[str, Any]:
        """
        Classify market regime using price/volume series (for Risk and Backtesting).
        """
        if len(prices) < self.lookback_period:
            return {
                "regime": RegimeType.RANGING.value,
                "confidence": 0.3,
                "confidence_score": 0.3,
                "maturity": 0.0,
                "stability": 0.0,
                "veto": True,
                "details": {"reason": "insufficient_data"}
            }

        res = self.classifier.classify_regime(prices, volumes)
        confidence = res.get("confidence", 0.3)
        regime = res.get("regime", RegimeType.RANGING.value)
        veto = res.get("veto", True)

        return {
            "regime": regime,
            "confidence": confidence,
            "confidence_score": confidence,
            "maturity": res.get("maturity", 0.0),
            "stability": res.get("stability", 0.0),
            "veto": veto,
            "details": res.get("details", {})
        }

    def detect_regime_from_indicators(self, volatility: float, trend: float) -> str:
        """
        Classify market regime from pre-calculated volatility/trend indicators (for Strategy Selection).
        """
        if volatility > 0.3:
            return "HIGH_VOLATILITY"
        elif abs(trend) > 0.1:
            return "BULL_TREND" if trend > 0 else "BEAR_TREND"
        return "NEUTRAL"
