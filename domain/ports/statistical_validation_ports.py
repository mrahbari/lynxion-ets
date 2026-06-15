"""Statistical-validation ports (E3.T9, gap-closure F11/F12).

The statistical-validation services were fully implemented but **untasked** —
they had no port seam and were not resolvable from the composition root. This
module defines one port per service so callers depend on a contract rather than
the concrete infrastructure class; the existing implementations in
``infrastructure/statistical_validation/`` structurally satisfy these ports and
are wired into :mod:`bootstrap.container` unchanged (no formula is altered).

Ports (1:1 with the canonical service classes):

* :class:`ConfidenceCalibrationPort` — ``ConfidenceCalibrator``
* :class:`RandomnessFirewallPort` — ``RandomnessExposureFirewall``
* :class:`StatisticalAuthorityPort` — ``StatisticalAuthorityScoreEngine``
* :class:`HistoricalDataTrackingPort` — ``HistoricalDataTracker``
* :class:`DecisionDefensibilityPort` — ``DecisionDefensibilityValidator``
"""
from typing import Protocol, Any, Dict, List, Tuple


class ConfidenceCalibrationPort(Protocol):
    """Calibrates raw confidence scores to reflect actual accuracy (F12)."""

    def add_calibration_sample(self, raw_confidence: float, actual_outcome: bool) -> None:
        """Record a (confidence, outcome) pair for calibration."""
        ...

    def calibrate_confidence(self, raw_confidence: float) -> float:
        """Return the calibrated confidence for ``raw_confidence``."""
        ...


class RandomnessFirewallPort(Protocol):
    """Gates component actions that risk exposure to randomness (F12)."""

    def apply_firewall_controls(self, component: str, data: Dict[str, Any],
                                historical_data: List[Dict[str, Any]]) -> Tuple[bool, List[Any]]:
        """Return ``(allow, alerts)`` for a component action."""
        ...


class StatisticalAuthorityPort(Protocol):
    """Computes statistical-authority scores per component (F11)."""

    def calculate_watcher_authority(self, historical_observations: List[Dict[str, Any]],
                                    current_observation: Dict[str, Any]) -> Any: ...

    def calculate_engine_authority(self, *args, **kwargs) -> Any: ...

    def calculate_fusion_authority(self, *args, **kwargs) -> Any: ...

    def calculate_strategy_authority(self, *args, **kwargs) -> Any: ...

    def calculate_broker_authority(self, *args, **kwargs) -> Any: ...

    def calculate_broker_close_authority(self, *args, **kwargs) -> Any: ...


class HistoricalDataTrackingPort(Protocol):
    """Stores per-component / per-symbol historical observations (F11/F12)."""

    def add_watcher_observation(self, symbol: str, observation_data: Dict[str, Any]) -> None: ...

    def add_engine_interpretation(self, symbol: str, interpretation_data: Dict[str, Any]) -> None: ...

    def add_fusion_result(self, symbol: str, fusion_data: Dict[str, Any]) -> None: ...

    def add_strategy_decision(self, symbol: str, decision_data: Dict[str, Any]) -> None: ...

    def add_broker_execution(self, symbol: str, execution_data: Dict[str, Any]) -> None: ...

    def add_broker_close(self, symbol: str, close_data: Dict[str, Any]) -> None: ...

    def get_all_history_for_symbol(self, symbol: str) -> Dict[str, List[Dict[str, Any]]]: ...


class DecisionDefensibilityPort(Protocol):
    """Validates that decisions are mathematically defensible (F12)."""

    def validate_watcher_decision(self, watcher_data: Dict[str, Any],
                                  historical_data: List[Dict[str, Any]]) -> Any: ...

    def validate_engine_decision(self, *args, **kwargs) -> Any: ...

    def validate_fusion_decision(self, *args, **kwargs) -> Any: ...

    def validate_strategy_decision(self, *args, **kwargs) -> Any: ...

    def validate_broker_decision(self, *args, **kwargs) -> Any: ...

    def validate_broker_close_decision(self, *args, **kwargs) -> Any: ...
