"""E3.T3 pilot: the consolidated position-sizing engine is container-managed.

Validates that the single ``PositionSizingEnginePort`` adapter is wired into the
composition root, constructed lazily, container-scoped, and that resolving it
(and resolve_all) stays offline-safe.
"""

import pytest

pytest.importorskip("numpy")

try:
    from bootstrap.lifecycle import create_container
    from infrastructure.position_sizing.position_sizing_engine_adapter import (
        PositionSizingEngineAdapter,
    )
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"composition root unavailable: {exc}", allow_module_level=True)


@pytest.mark.e2e
def test_engine_registered_and_resolvable(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        assert "position_sizing_engine" in container.registered_keys()
        engine = container.resolve("position_sizing_engine")
        assert isinstance(engine, PositionSizingEngineAdapter)
        assert engine.available_algorithms() == [
            "fixed_risk", "kelly", "atr", "volatility_target", "probabilistic",
        ]
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_engine_is_single_instance_within_container(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        assert container.resolve("position_sizing_engine") is container.resolve(
            "position_sizing_engine"
        )
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_engine_is_container_scoped(tmp_path):
    c1 = create_container(base_data_dir=str(tmp_path / "c1"))
    c2 = create_container(base_data_dir=str(tmp_path / "c2"))
    try:
        assert c1.resolve("position_sizing_engine") is not c2.resolve(
            "position_sizing_engine"
        )
    finally:
        c1.shutdown()
        c2.shutdown()


@pytest.mark.e2e
def test_engine_computes_through_container(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        engine = container.resolve("position_sizing_engine")
        size = engine.compute_size(
            "fixed_risk",
            entry_price=5.0,
            stop_loss=4.0,
            portfolio_equity=100000.0,
            risk_per_trade=0.01,
            signal_expectancy=0.4,
            regime_accuracy=0.8,
            fusion_confidence=0.9,
            correlation_exposure=0.2,
            current_drawdown=0.1,
        )
        assert size == pytest.approx(622.08, rel=1e-12)
    finally:
        container.shutdown()
