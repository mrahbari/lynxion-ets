"""E4.T3 — unit tests for infrastructure/market_regime/regime_detector.py.

detect_regime is a pure function of the price/volume series (no randomness),
so results are deterministic. Tests pin the insufficient-data guard exactly and
assert the structural/numeric contract of the full path (avoiding brittleness on
the specific regime label, which is classifier-internal).
"""

import pytest

from infrastructure.market_regime.regime_detector import RegimeDetector
from infrastructure.market_regime._regime_classifiers import RegimeType

_VALID_REGIMES = {rt.value for rt in RegimeType}


@pytest.mark.unit
def test_insufficient_data_returns_low_confidence_veto():
    det = RegimeDetector(lookback_period=50)
    result = det.detect_regime(prices=[100.0, 101.0, 102.0])   # 3 < 50
    assert result["regime"] == RegimeType.RANGING.value
    assert result["confidence"] == 0.3
    assert result["confidence_score"] == 0.3
    assert result["veto"] is True
    assert result["details"]["reason"] == "insufficient_data"


@pytest.mark.unit
def test_full_path_returns_well_formed_contract():
    det = RegimeDetector(lookback_period=50)
    prices = [100.0 + i for i in range(60)]    # deterministic linear uptrend
    result = det.detect_regime(prices=prices)

    assert set(result) >= {"regime", "confidence", "confidence_score", "maturity", "stability", "veto", "details"}
    assert result["regime"] in _VALID_REGIMES
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["confidence_score"] == result["confidence"]   # documented alias
    assert isinstance(result["veto"], bool)


@pytest.mark.unit
def test_detector_is_deterministic_for_identical_input():
    prices = [100.0 + (i % 7) for i in range(60)]
    a = RegimeDetector(lookback_period=50).detect_regime(prices=prices)
    b = RegimeDetector(lookback_period=50).detect_regime(prices=prices)
    assert a["regime"] == b["regime"]
    assert a["confidence"] == b["confidence"]
