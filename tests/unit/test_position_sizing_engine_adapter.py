"""E4.T5 — unit tests for infrastructure/position_sizing/position_sizing_engine_adapter.py.

The adapter delegates to PositionSizingService (constructed in __init__). For an
isolated unit test we swap the internal service with a recording fake and pin
the delegation contract: `algorithm` passed positionally, the sizing factors as
keywords, return value passed through unchanged. NOT the E5-B sizing engine.
"""

import pytest

from infrastructure.position_sizing.position_sizing_engine_adapter import (
    PositionSizingEngineAdapter,
)


class _FakeSizingService:
    def __init__(self):
        self.calls = []

    def compute_size(self, algorithm, **kwargs):
        self.calls.append((algorithm, kwargs))
        return 12.34

    def get_available_models(self):
        return ["fixed_fractional", "kelly"]


@pytest.fixture
def adapter_with_fake():
    adapter = PositionSizingEngineAdapter(service=_FakeSizingService())   # isolate from the real service
    return adapter


@pytest.mark.unit
def test_compute_size_forwards_algorithm_and_factors(adapter_with_fake):
    result = adapter_with_fake.compute_size(
        "kelly", entry_price=100.0, stop_loss=95.0,
        portfolio_equity=10_000.0, risk_per_trade=0.01, win_rate=0.6,
    )
    assert result == 12.34
    algorithm, kwargs = adapter_with_fake._service.calls[0]
    assert algorithm == "kelly"
    assert kwargs == {
        "entry_price": 100.0, "stop_loss": 95.0,
        "portfolio_equity": 10_000.0, "risk_per_trade": 0.01, "win_rate": 0.6,
    }


@pytest.mark.unit
def test_available_algorithms_delegates_to_service(adapter_with_fake):
    assert adapter_with_fake.available_algorithms() == ["fixed_fractional", "kelly"]
