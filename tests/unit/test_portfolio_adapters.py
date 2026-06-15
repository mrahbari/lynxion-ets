"""E4.T3 — unit tests for infrastructure/portfolio/portfolio_adapters.py.

Deterministic allocation/sizing/optimization adapters (the consolidated, simplified
implementations behind the portfolio ports). No I/O. Pins the current contract of
each adapter so future E5-B work can't silently change allocation behavior.
"""

from decimal import Decimal

import pytest

from domain.value_objects import Symbol, Percentage
from infrastructure.portfolio.portfolio_adapters import (
    EqualWeightPortfolioAdapter,
    RiskParityPortfolioAdapter,
    VolatilityTargetPortfolioAdapter,
    FixedRiskPositionSizingAdapter,
    KellyCriterionPositionSizingAdapter,
    MeanVarianceOptimizationAdapter,
)

BTC, ETH, BNB = Symbol("BTCUSDT"), Symbol("ETHUSDT"), Symbol("BNBUSDT")


@pytest.mark.unit
@pytest.mark.parametrize("Adapter", [
    EqualWeightPortfolioAdapter, RiskParityPortfolioAdapter, VolatilityTargetPortfolioAdapter,
])
def test_allocation_splits_capital_evenly(Adapter):
    alloc = Adapter().calculate_allocation(300.0, [BTC, ETH, BNB])
    assert set(alloc) == {BTC, ETH, BNB}
    assert all(v == 100.0 for v in alloc.values())
    assert sum(alloc.values()) == pytest.approx(300.0)


@pytest.mark.unit
@pytest.mark.parametrize("Adapter", [
    EqualWeightPortfolioAdapter, RiskParityPortfolioAdapter, VolatilityTargetPortfolioAdapter,
])
def test_allocation_empty_symbols_returns_empty(Adapter):
    assert Adapter().calculate_allocation(1000.0, []) == {}


@pytest.mark.unit
def test_rebalance_returns_empty_order_list_and_metrics_carry_method_tag():
    assert EqualWeightPortfolioAdapter().rebalance_portfolio({}) == []
    assert EqualWeightPortfolioAdapter().get_portfolio_metrics()["allocation_method"] == "equal_weight"
    assert RiskParityPortfolioAdapter().get_portfolio_metrics()["allocation_method"] == "risk_parity"
    assert VolatilityTargetPortfolioAdapter().get_portfolio_metrics()["allocation_method"] == "volatility_target"


@pytest.mark.unit
@pytest.mark.parametrize("Adapter", [FixedRiskPositionSizingAdapter, KellyCriterionPositionSizingAdapter])
def test_position_sizing_adapters_return_zero_placeholder(Adapter):
    # Per the risk-governance rule, sizing is delegated to the risk module;
    # these adapters intentionally return 0.0 to preserve interface compatibility.
    assert Adapter().calculate_position_size(BTC, 10_000.0, 0.02) == 0.0


@pytest.mark.unit
def test_mean_variance_optimization_returns_equal_percentages():
    alloc = MeanVarianceOptimizationAdapter().optimize_allocation([BTC, ETH], constraints={})
    assert set(alloc) == {BTC, ETH}
    assert all(isinstance(p, Percentage) for p in alloc.values())
    assert all(p.value == Decimal("0.5") for p in alloc.values())


@pytest.mark.unit
def test_mean_variance_optimization_empty_assets_returns_empty():
    assert MeanVarianceOptimizationAdapter().optimize_allocation([], constraints={}) == {}
