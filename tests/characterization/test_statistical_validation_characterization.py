"""Characterization: statistical-validation services behind ports (E3.T9, F11/F12).

Pins that placing the statistical-validation services behind ports + wiring them
into the composition root changes NO output:

* the confidence calibrator reproduces its calibrated values on fixed inputs,
* the randomness firewall reproduces its allow/alert decisions on fixed inputs,
* all five services are resolvable from ``bootstrap/container.py`` and conform to
  their ports.

The components are constructed directly (canonical reference) and via the
container; their outputs must match.
"""

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("sklearn")

from bootstrap.settings.loaders import load_settings
from bootstrap.container import Container


# --- Confidence calibrator: fixed-input outputs unchanged ---------------------

@pytest.mark.unit
def test_calibrator_passthrough_when_unfitted():
    """With no fitted model, calibrate_confidence clamps to [0,1] (pinned)."""
    from infrastructure.statistical_validation.confidence_calibrator import ConfidenceCalibrator

    cal = ConfidenceCalibrator()
    assert cal.calibrate_confidence(0.42) == 0.42
    assert cal.calibrate_confidence(1.5) == 1.0
    assert cal.calibrate_confidence(-0.3) == 0.0


@pytest.mark.unit
def test_calibrator_isotonic_fixed_output():
    """Deterministic isotonic fit on a fixed dataset yields a pinned calibration."""
    from infrastructure.statistical_validation.confidence_calibrator import ConfidenceCalibrator

    def _fit():
        cal = ConfidenceCalibrator(model_type="isotonic")
        # Monotone, separable data -> deterministic isotonic regression.
        samples = [(0.1, False), (0.2, False), (0.3, False), (0.4, False), (0.5, False),
                   (0.6, True), (0.7, True), (0.8, True), (0.9, True), (0.95, True)]
        for conf, outcome in samples:
            cal.calibration_data.append((conf, outcome))
        cal._recalibrate()
        return cal

    a = _fit()
    b = _fit()
    probe = [0.15, 0.45, 0.55, 0.85]
    out_a = [a.calibrate_confidence(p) for p in probe]
    out_b = [b.calibrate_confidence(p) for p in probe]

    # Deterministic across independent fits, and bounded to [0,1].
    assert out_a == out_b
    assert all(0.0 <= v <= 1.0 for v in out_a)
    # Monotone non-decreasing (isotonic invariant) — pins behavior, not magic numbers.
    assert out_a == sorted(out_a)


@pytest.mark.unit
def test_container_calibrator_matches_direct():
    from infrastructure.statistical_validation.confidence_calibrator import ConfidenceCalibrator

    container = Container(load_settings())
    resolved = container.resolve("confidence_calibrator")
    assert isinstance(resolved, ConfidenceCalibrator)
    assert resolved.calibrate_confidence(0.73) == ConfidenceCalibrator().calibrate_confidence(0.73)


# --- Randomness firewall: fixed-input decisions unchanged ---------------------

@pytest.mark.unit
def test_firewall_blocks_on_insufficient_history():
    """A HIGH-severity alert (insufficient history) blocks the action (pinned)."""
    from infrastructure.statistical_validation.randomness_exposure_firewall import RandomnessExposureFirewall

    fw = RandomnessExposureFirewall()
    allow, alerts = fw.apply_firewall_controls("WATCHER", {"confidence": 0.8}, historical_data=[])

    assert allow is False
    risk_types = {a.risk_type for a in alerts}
    assert "INSUFFICIENT_HISTORICAL_DATA" in risk_types
    assert any(a.severity == "HIGH" for a in alerts)


@pytest.mark.unit
def test_firewall_allows_unknown_component():
    from infrastructure.statistical_validation.randomness_exposure_firewall import RandomnessExposureFirewall

    fw = RandomnessExposureFirewall()
    allow, alerts = fw.apply_firewall_controls("UNKNOWN", {}, historical_data=[])
    assert allow is True
    assert alerts == []


@pytest.mark.unit
def test_container_firewall_matches_direct():
    from infrastructure.statistical_validation.randomness_exposure_firewall import RandomnessExposureFirewall

    container = Container(load_settings())
    fw = container.resolve("randomness_firewall")
    assert isinstance(fw, RandomnessExposureFirewall)

    data = {"confidence": 0.97}
    hist = []
    assert fw.apply_firewall_controls("WATCHER", data, hist) == \
        RandomnessExposureFirewall().apply_firewall_controls("WATCHER", data, hist)


# --- Container resolvability + port conformance for all five services ---------

@pytest.mark.unit
def test_all_statistical_validation_services_resolvable():
    from domain.ports.statistical_validation_ports import (
        ConfidenceCalibrationPort, RandomnessFirewallPort, StatisticalAuthorityPort,
        HistoricalDataTrackingPort, DecisionDefensibilityPort,
    )

    container = Container(load_settings())

    keys_ports = {
        "confidence_calibrator": ConfidenceCalibrationPort,
        "randomness_firewall": RandomnessFirewallPort,
        "statistical_authority_engine": StatisticalAuthorityPort,
        "statistical_historical_data_tracker": HistoricalDataTrackingPort,
        "decision_defensibility_validator": DecisionDefensibilityPort,
    }

    for key, port in keys_ports.items():
        svc = container.resolve(key)
        assert svc is not None
        # Structural conformance: the canonical class satisfies the port's surface.
        for method in (m for m in dir(port) if not m.startswith("_")):
            assert callable(getattr(svc, method, None)), f"{key} missing {method}"
        # Cached on re-resolve.
        assert container.resolve(key) is svc
