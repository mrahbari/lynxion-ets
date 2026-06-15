"""E4.T6 — unit tests for infrastructure/statistical_validation/randomness_exposure_firewall.py.

Deterministic statistical guards that emit RandomnessExposureAlert lists. Tests
pin the watcher insufficient-data / overfitting branches and the engine flip-rate
branch, plus a smoke check that all six check_*_randomness methods share the
(component_data, historical_data) -> list contract and never raise on empty input.
"""

import pytest

from infrastructure.statistical_validation.randomness_exposure_firewall import (
    RandomnessExposureFirewall,
)

_CHECKS = [
    "check_watcher_randomness", "check_engine_randomness", "check_fusion_randomness",
    "check_strategy_randomness", "check_broker_randomness", "check_broker_close_randomness",
]


@pytest.fixture
def fw():
    return RandomnessExposureFirewall()


@pytest.mark.unit
def test_watcher_flags_insufficient_history(fw):
    alerts = fw.check_watcher_randomness({"confidence": 0.7}, historical_data=[])
    risk_types = {a.risk_type for a in alerts}
    assert "INSUFFICIENT_HISTORICAL_DATA" in risk_types
    insuff = next(a for a in alerts if a.risk_type == "INSUFFICIENT_HISTORICAL_DATA")
    assert insuff.component == "WATCHER"
    assert insuff.severity == "HIGH"
    assert insuff.mitigation_action == "BLOCK_OBSERVATION"


@pytest.mark.unit
def test_watcher_flags_overfitting_on_high_confidence_low_history(fw):
    alerts = fw.check_watcher_randomness({"confidence": 0.99}, historical_data=[{"value": 1}] * 10)
    risk_types = {a.risk_type for a in alerts}
    assert {"INSUFFICIENT_HISTORICAL_DATA", "POTENTIAL_OVERFITTING"} <= risk_types


@pytest.mark.unit
def test_watcher_no_confidence_and_short_history_is_clean(fw):
    # No 'confidence' key -> confidence block skipped; <30 history -> volatility block skipped.
    assert fw.check_watcher_randomness({}, historical_data=[]) == []


@pytest.mark.unit
def test_engine_flags_high_flip_rate(fw):
    # Alternating interpreted_signal across recent history -> HIGH_FLIP_RATE.
    # history[-1] is BUY, so current must differ (SELL) to enter the flip-count branch.
    history = [{"interpreted_signal": "BUY" if i % 2 else "SELL"} for i in range(6)]
    alerts = fw.check_engine_randomness({"interpreted_signal": "SELL"}, historical_data=history)
    assert any(a.risk_type == "HIGH_FLIP_RATE" and a.component == "ENGINE" for a in alerts)


@pytest.mark.unit
@pytest.mark.parametrize("method_name", _CHECKS)
def test_all_checks_return_list_and_dont_raise_on_empty(fw, method_name):
    result = getattr(fw, method_name)({}, [])
    assert isinstance(result, list)
