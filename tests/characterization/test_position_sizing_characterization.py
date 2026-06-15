"""Characterization: position-sizing algorithms (E3.T3).

Pins the CURRENT numeric output of every reachable position-sizing algorithm so
the E3.T3 consolidation (single ``PositionSizingEnginePort`` + adapter) cannot
change sizing behavior. Inputs and expected outputs are fixed.

The reachable algorithms are the five models exposed by
``application.position_sizing.enterprise_position_sizing.PositionSizingService``
(``fixed_risk``, ``kelly``, ``atr``, ``volatility_target``, ``probabilistic``) —
the only sizing engine with a (legacy) consumer. The other sizing modules are
unreferenced; see the E3.T3 discovery report.

Two input cases are pinned per algorithm:

* CASE_FORMULA — small price / wide factors so the core formula drives the
  result (distinct per algorithm), below the price-tier constraints.
* CASE_CLAMP   — mid price where the ``max_size_by_price * 0.1`` constraint binds
  (identical across algorithms), pinning the constraint/tier logic.
"""

import pytest

pytest.importorskip("numpy")

from application.position_sizing.enterprise_position_sizing import PositionSizingService


ALGORITHMS = ["fixed_risk", "kelly", "atr", "volatility_target", "probabilistic"]

# Formula-driven case (stays below the price-tier / max-by-price caps).
CASE_FORMULA = dict(
    entry_price=5.0,
    stop_loss=4.0,
    portfolio_equity=100000.0,
    risk_per_trade=0.01,
    volatility=0.5,
    signal_expectancy=0.4,
    regime_accuracy=0.8,
    fusion_confidence=0.9,
    correlation_exposure=0.2,
    current_drawdown=0.1,
)
# Kelly takes additional win/loss inputs.
CASE_FORMULA_KELLY_EXTRA = dict(win_rate=0.6, avg_win_rate=0.12, avg_loss_rate=0.06)

EXPECTED_FORMULA = {
    "fixed_risk": 622.08,
    "kelly": 1244.1600000000003,
    "atr": 1244.16,
    "volatility_target": 2000.0,
    "probabilistic": 378.43200000000013,
}

# Constraint-driven case: max_size_by_price * 0.1 == (100000/100)*0.1 == 100 binds
# for every algorithm.
CASE_CLAMP = dict(
    entry_price=100.0,
    stop_loss=98.0,
    portfolio_equity=100000.0,
    risk_per_trade=0.01,
)
EXPECTED_CLAMP = {algo: 100.0 for algo in ALGORITHMS}


def _args(algo, case):
    args = dict(case)
    if algo == "kelly" and case is CASE_FORMULA:
        args.update(CASE_FORMULA_KELLY_EXTRA)
    return args


@pytest.mark.unit
@pytest.mark.parametrize("algo", ALGORITHMS)
def test_legacy_enterprise_service_formula_case(algo):
    service = PositionSizingService()
    result = service.compute_size(algo, **_args(algo, CASE_FORMULA))
    assert result == pytest.approx(EXPECTED_FORMULA[algo], rel=1e-12)


@pytest.mark.unit
@pytest.mark.parametrize("algo", ALGORITHMS)
def test_legacy_enterprise_service_clamp_case(algo):
    service = PositionSizingService()
    result = service.compute_size(algo, **_args(algo, CASE_CLAMP))
    assert result == pytest.approx(EXPECTED_CLAMP[algo], rel=1e-12)


@pytest.mark.unit
def test_legacy_available_models_unchanged():
    assert PositionSizingService().get_available_models() == ALGORITHMS


# --- Consolidated adapter (E3.T3): must equal legacy outputs byte-for-byte ----

@pytest.mark.unit
@pytest.mark.parametrize("algo", ALGORITHMS)
def test_adapter_formula_case_matches_expected(algo):
    from infrastructure.position_sizing.position_sizing_engine_adapter import (
        PositionSizingEngineAdapter,
    )
    adapter = PositionSizingEngineAdapter(service=PositionSizingService())
    result = adapter.compute_size(algo, **_args(algo, CASE_FORMULA))
    assert result == pytest.approx(EXPECTED_FORMULA[algo], rel=1e-12)


@pytest.mark.unit
@pytest.mark.parametrize("algo", ALGORITHMS)
def test_adapter_clamp_case_matches_expected(algo):
    from infrastructure.position_sizing.position_sizing_engine_adapter import (
        PositionSizingEngineAdapter,
    )
    adapter = PositionSizingEngineAdapter(service=PositionSizingService())
    result = adapter.compute_size(algo, **_args(algo, CASE_CLAMP))
    assert result == pytest.approx(EXPECTED_CLAMP[algo], rel=1e-12)


@pytest.mark.unit
@pytest.mark.parametrize("algo", ALGORITHMS)
def test_adapter_equals_legacy(algo):
    from infrastructure.position_sizing.position_sizing_engine_adapter import (
        PositionSizingEngineAdapter,
    )
    legacy = PositionSizingService().compute_size(algo, **_args(algo, CASE_FORMULA))
    adapted = PositionSizingEngineAdapter(service=PositionSizingService()).compute_size(algo, **_args(algo, CASE_FORMULA))
    assert adapted == legacy


@pytest.mark.unit
def test_adapter_available_algorithms():
    from infrastructure.position_sizing.position_sizing_engine_adapter import (
        PositionSizingEngineAdapter,
    )
    assert PositionSizingEngineAdapter(service=PositionSizingService()).available_algorithms() == ALGORITHMS


@pytest.mark.unit
def test_probabilistic_module_singleton_retired():
    """The module-level ``position_sizing_service`` is no longer instantiated at
    import time; access is served lazily by the PEP 562 accessor."""
    import infrastructure.position_sizing.probabilistic_position_sizer as ppz

    assert hasattr(ppz, "__getattr__")
    assert "position_sizing_service" not in vars(ppz)
    # Lazy access still works for backward compatibility.
    assert ppz.position_sizing_service is not None
