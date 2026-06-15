"""E4.T3 — unit tests for infrastructure/statistical_validation/statistical_authority_engine.py.

Binomial/Wilson statistics over historical-outcome dicts (deterministic via scipy).
Covers the insufficient-data guard, the significant-evidence PASS path, and the
chance-level FAIL path for the watcher + engine authorities (which exercise the
shared _wilson_score_interval / _calculate_authority_score helpers). No I/O.
"""

import pytest

from infrastructure.statistical_validation.statistical_authority_engine import (
    StatisticalAuthorityScoreEngine,
    ComponentType,
)


def _obs(n, correct):
    """n observation dicts, the first `correct` marked was_correct=True."""
    return [{"was_correct": i < correct} for i in range(n)]


@pytest.mark.unit
def test_watcher_insufficient_data():
    eng = StatisticalAuthorityScoreEngine()
    score = eng.calculate_watcher_authority(_obs(20, 20), current_observation={})
    assert score.component is ComponentType.WATCHER
    assert score.validation_status == "INSUFFICIENT_DATA"
    assert score.score == 0.0
    assert score.sample_size == 20
    assert score.statistical_test == "insufficient_data"


@pytest.mark.unit
def test_watcher_significant_accuracy_passes():
    eng = StatisticalAuthorityScoreEngine()
    score = eng.calculate_watcher_authority(_obs(50, 50), current_observation={})   # 100% correct
    assert score.component is ComponentType.WATCHER
    assert score.validation_status == "PASS"
    assert score.p_value < 0.05
    assert 0.0 < score.score <= 1.0
    assert score.sample_size == 50
    assert score.statistical_test == "binomial_accuracy_test"
    lo, hi = score.confidence_interval
    assert lo <= hi


@pytest.mark.unit
def test_watcher_chance_level_fails():
    eng = StatisticalAuthorityScoreEngine()
    score = eng.calculate_watcher_authority(_obs(50, 25), current_observation={})   # 50% accuracy
    assert score.validation_status == "FAIL"


@pytest.mark.unit
def test_engine_insufficient_and_significant():
    eng = StatisticalAuthorityScoreEngine()
    insufficient = eng.calculate_engine_authority(_obs(10, 10), current_interpretation={})
    assert insufficient.component is ComponentType.ENGINE
    assert insufficient.validation_status == "INSUFFICIENT_DATA"

    strong = eng.calculate_engine_authority(_obs(50, 50), current_interpretation={})
    assert strong.component is ComponentType.ENGINE
    assert strong.validation_status == "PASS"
    assert strong.p_value < 0.05
    assert 0.0 < strong.score <= 1.0


# All six authority methods share the (historical_list, current_dict) shape and the
# same minimum-sample-size guard; cover each so every ComponentType is exercised.
_METHODS = [
    ("calculate_watcher_authority", ComponentType.WATCHER),
    ("calculate_engine_authority", ComponentType.ENGINE),
    ("calculate_fusion_authority", ComponentType.FUSION),
    ("calculate_strategy_authority", ComponentType.STRATEGY),
    ("calculate_broker_authority", ComponentType.BROKER),
    ("calculate_broker_close_authority", ComponentType.BROKER_CLOSE),
]


@pytest.mark.unit
@pytest.mark.parametrize("method_name,component", _METHODS)
def test_all_authorities_guard_on_insufficient_data(method_name, component):
    eng = StatisticalAuthorityScoreEngine()
    score = getattr(eng, method_name)(_obs(5, 5), {})
    assert score.component is component
    assert score.validation_status == "INSUFFICIENT_DATA"
    assert score.score == 0.0
    assert score.sample_size == 5


@pytest.mark.unit
@pytest.mark.parametrize("method_name,component", _METHODS)
def test_all_authorities_full_path_well_formed(method_name, component):
    eng = StatisticalAuthorityScoreEngine()
    score = getattr(eng, method_name)(_obs(50, 50), {})
    assert score.component is component
    # sample_size semantics differ per method (e.g. strategy counts only
    # decisions carrying return_pct), so just assert it is a non-negative int.
    assert isinstance(score.sample_size, int) and score.sample_size >= 0
    assert 0.0 <= score.score <= 1.0
    assert score.validation_status in {"PASS", "FAIL"}
    lo, hi = score.confidence_interval
    assert lo <= hi
