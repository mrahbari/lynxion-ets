"""Unit tests for DerivativesFeatureEngine."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from domain.value_objects import Symbol, ExchangeTimestamp, Quantity, Money
from domain.entities.market_data import FundingRate, OpenInterest
from infrastructure.data.derivatives_feature_engine import DerivativesFeatureEngine


def test_funding_annualized_and_sma():
    symbol = Symbol("BTCUSDT")
    f1 = FundingRate(symbol, Decimal("0.0001"), ExchangeTimestamp(1000), ExchangeTimestamp(28801000))
    f2 = FundingRate(symbol, Decimal("0.0002"), ExchangeTimestamp(2000), ExchangeTimestamp(28802000))
    f3 = FundingRate(symbol, Decimal("0.0003"), ExchangeTimestamp(3000), ExchangeTimestamp(28803000))

    rates = [f1, f2, f3]
    vec = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(3000), rates, [])

    # Annualized = 0.0003 * 3 * 365 * 100% = 32.85%
    assert vec.funding_annualized == pytest.approx(32.85)

    # SMA 24h = (0.0001 + 0.0002 + 0.0003) / 3 = 0.0002
    assert vec.funding_sma_24h == pytest.approx(0.0002)


def test_oi_change_1h_pct():
    symbol = Symbol("ETHUSDT")
    o1 = OpenInterest(symbol, Quantity(Decimal("1000"), "ETHUSDT"), ExchangeTimestamp(1000))
    o2 = OpenInterest(symbol, Quantity(Decimal("1100"), "ETHUSDT"), ExchangeTimestamp(2000))

    vec = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(2000), [], [o1, o2])

    # OI change = (1100 - 1000) / 1000 = 0.10 (+10%)
    assert vec.oi_change_1h_pct == pytest.approx(0.10)


def test_warmup_behavior():
    symbol = Symbol("BTCUSDT")
    # Less than required observations
    rates = [
        FundingRate(symbol, Decimal("0.0001"), ExchangeTimestamp(i * 1000), ExchangeTimestamp(i * 1000 + 28800000))
        for i in range(1, 51)
    ]
    oi_list = [
        OpenInterest(symbol, Quantity(Decimal("1000"), "BTCUSDT"), ExchangeTimestamp(i * 1000))
        for i in range(1, 51)
    ]

    vec = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(50000), rates, oi_list)

    assert vec.is_warmed_up is False
    assert vec.funding_zscore_30d is None
    assert vec.funding_percentile_90d is None
    assert vec.oi_zscore_14d is None


def test_zscore_and_percentile_correctness():
    symbol = Symbol("BTCUSDT")
    # Create 270 rates with increasing values
    rates = [
        FundingRate(symbol, Decimal(str(i * 0.00001)), ExchangeTimestamp(i * 1000), ExchangeTimestamp(i * 1000 + 28800000))
        for i in range(1, 271)
    ]
    # Create 336 OI records
    oi_list = [
        OpenInterest(symbol, Quantity(Decimal(str(1000 + i * 10)), "BTCUSDT"), ExchangeTimestamp(i * 1000))
        for i in range(1, 337)
    ]

    vec = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(336000), rates, oi_list)

    assert vec.is_warmed_up is True
    assert vec.funding_zscore_30d is not None
    assert vec.funding_percentile_90d == pytest.approx(1.0)  # Max rate is at 100th percentile
    assert vec.oi_zscore_14d is not None
    assert vec.oi_zscore_14d > 0.0  # Latest OI is above mean


def test_pit_leakage_prevention():
    symbol = Symbol("BTCUSDT")
    f1 = FundingRate(symbol, Decimal("0.0001"), ExchangeTimestamp(1000), ExchangeTimestamp(28801000))
    f2 = FundingRate(symbol, Decimal("0.0002"), ExchangeTimestamp(2000), ExchangeTimestamp(28802000))
    f_future = FundingRate(symbol, Decimal("0.0099"), ExchangeTimestamp(5000), ExchangeTimestamp(28805000))

    rates = [f1, f2, f_future]

    # Target timestamp T = 2000; f_future (T=5000) MUST be excluded!
    vec = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(2000), rates, [])

    # Latest included rate is f2 (0.0002), NOT f_future (0.0099)
    assert vec.funding_annualized == pytest.approx(0.0002 * 3 * 365 * 100)


def test_missing_ohlcv_handling():
    symbol = Symbol("BTCUSDT")
    f1 = FundingRate(symbol, Decimal("0.0001"), ExchangeTimestamp(1000), ExchangeTimestamp(28801000))
    o1 = OpenInterest(symbol, Quantity(Decimal("1000"), "BTCUSDT"), ExchangeTimestamp(1000))

    # OHLCV is None
    vec = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(1000), [f1], [o1], ohlcv_records=None)

    assert vec.price_oi_divergence_score is None
    assert vec.oi_to_volume_ratio_24h is None
    assert vec.oi_liquidation_vulnerability_index is None


def test_deterministic_output():
    symbol = Symbol("SOLUSDT")
    f1 = FundingRate(symbol, Decimal("0.0002"), ExchangeTimestamp(1000), ExchangeTimestamp(28801000))
    o1 = OpenInterest(symbol, Quantity(Decimal("5000"), "SOLUSDT"), ExchangeTimestamp(1000))

    v1 = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(1000), [f1], [o1])
    v2 = DerivativesFeatureEngine.compute_vector(symbol, ExchangeTimestamp(1000), [f1], [o1])

    assert v1 == v2
