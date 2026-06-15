"""E4.T3 — unit tests for infrastructure/statistical_validation/confidence_calibrator.py.

Isotonic/Platt confidence calibration. Deterministic (sklearn isotonic is
deterministic given data). save/load exercised against a tmp file. No network.
"""

import pytest

from infrastructure.statistical_validation.confidence_calibrator import ConfidenceCalibrator


@pytest.mark.unit
def test_uncalibrated_clamps_to_unit_interval():
    c = ConfidenceCalibrator()
    assert c.calibrate_confidence(1.5) == 1.0
    assert c.calibrate_confidence(-0.2) == 0.0
    assert c.calibrate_confidence(0.7) == 0.7   # passthrough when no model


@pytest.mark.unit
def test_window_trims_to_most_recent_samples():
    c = ConfidenceCalibrator(calibration_window=10)
    for i in range(15):
        c.add_calibration_sample(raw_confidence=i / 15.0, actual_outcome=bool(i % 2))
    assert len(c.calibration_data) == 10


@pytest.mark.unit
def test_no_model_until_threshold_samples():
    c = ConfidenceCalibrator()
    for i in range(5):
        c.add_calibration_sample(0.5, True)
    assert c.calibration_model is None
    assert c.calibrate_confidence(0.9) == 0.9    # still raw passthrough


@pytest.mark.unit
def test_recalibration_is_monotonic_and_bounded():
    c = ConfidenceCalibrator(model_type="isotonic")
    # Clear monotone relationship: high raw confidence -> correct, low -> incorrect.
    for i in range(60):
        raw = (i % 10) / 10.0          # 0.0..0.9 repeating
        c.add_calibration_sample(raw_confidence=raw, actual_outcome=raw > 0.5)
    assert c.calibration_model is not None         # fitted after >=50 samples
    low = c.calibrate_confidence(0.1)
    high = c.calibrate_confidence(0.9)
    assert 0.0 <= low <= 1.0 and 0.0 <= high <= 1.0
    assert high >= low                              # isotonic preserves ordering


@pytest.mark.unit
def test_save_and_load_round_trip(tmp_path):
    c = ConfidenceCalibrator()
    for i in range(60):
        raw = (i % 10) / 10.0
        c.add_calibration_sample(raw, raw > 0.5)
    path = str(tmp_path / "calib.pkl")
    c.save_model(path)

    loaded = ConfidenceCalibrator()
    loaded.load_model(path)
    assert loaded.calibration_model is not None
    assert len(loaded.calibration_data) == len(c.calibration_data)


@pytest.mark.unit
def test_load_missing_file_is_noop(tmp_path):
    c = ConfidenceCalibrator()
    c.load_model(str(tmp_path / "absent.pkl"))
    assert c.calibration_model is None
