"""Unit tests for the Next Generation Liquidity Sweep (NGLS) feature pipeline (Milestone 3)."""

import pytest
from decimal import Decimal

from domain.value_objects import Symbol, Side, ExchangeTimestamp
from domain.entities import TradeTick, OrderBookSnapshot, OrderBookLevel
from infrastructure.data.ngls_feature_generator import NGLSFeatureGenerator


@pytest.fixture
def btc_symbol():
    return Symbol("BTC-USDT")


@pytest.fixture
def eth_symbol():
    return Symbol("ETH-USDT")


@pytest.fixture
def initial_snapshot(btc_symbol):
    from domain.value_objects import Price, Quantity
    return OrderBookSnapshot(
        symbol=btc_symbol,
        timestamp=ExchangeTimestamp(1700000000000),
        bids=[
            OrderBookLevel(Price(Decimal("45000.0"), btc_symbol), Quantity(Decimal("2.0"), "BTC")),
            OrderBookLevel(Price(Decimal("44990.0"), btc_symbol), Quantity(Decimal("3.0"), "BTC")),
        ],
        asks=[
            OrderBookLevel(Price(Decimal("45010.0"), btc_symbol), Quantity(Decimal("1.0"), "BTC")),
            OrderBookLevel(Price(Decimal("45020.0"), btc_symbol), Quantity(Decimal("4.0"), "BTC")),
        ],
        sequence_id=100
    )


@pytest.mark.unit
def test_feature_generation_imbalance_ratio(btc_symbol, initial_snapshot):
    """Verify that OBI ratios and velocities are calculated correctly from snapshots."""
    generator = NGLSFeatureGenerator(btc_symbol)
    
    # 1. Update with initial snapshot
    # bid_qty = 2.0, ask_qty = 1.0 -> obi = (2 - 1)/(2 + 1) = 0.3333...
    snap_dict = generator.update_feature_online(btc_symbol, initial_snapshot)
    assert Decimal(snap_dict["obi_ratio"]) == pytest.approx(Decimal("0.3333"), abs=Decimal("0.001"))
    assert Decimal(snap_dict["obi_velocity"]) == Decimal("0") # First call has no elapsed time
    
    # 2. Update with new snapshot after 2 seconds having different OBI
    # bid_qty = 1.0, ask_qty = 3.0 -> obi = (1 - 3)/(1 + 3) = -0.5
    from domain.value_objects import Price, Quantity
    new_snapshot = OrderBookSnapshot(
        symbol=btc_symbol,
        timestamp=ExchangeTimestamp(1700000002000), # 2 sec later
        bids=[OrderBookLevel(Price(Decimal("45000.0"), btc_symbol), Quantity(Decimal("1.0"), "BTC"))],
        asks=[OrderBookLevel(Price(Decimal("45010.0"), btc_symbol), Quantity(Decimal("3.0"), "BTC"))],
        sequence_id=102
    )
    snap_dict2 = generator.update_feature_online(btc_symbol, new_snapshot)
    assert Decimal(snap_dict2["obi_ratio"]) == Decimal("-0.5")
    
    # Velocity = (current_obi - previous_obi) / dt = (-0.5 - 0.3333333333333333) / 2 = -0.41666666666666663
    expected_velocity = (Decimal("-0.5") - (Decimal("1") / Decimal("3"))) / Decimal("2.0")
    assert Decimal(snap_dict2["obi_velocity"]) == pytest.approx(expected_velocity, abs=Decimal("0.0001"))


@pytest.mark.unit
def test_feature_generation_delta_and_cvd(btc_symbol):
    """Verify that trade delta aggregates and CVD track buy/sell volume updates correctly."""
    from domain.value_objects import Price, Quantity
    generator = NGLSFeatureGenerator(btc_symbol)

    # Apply 3 trade ticks
    # 1. Buy: qty 1.5, price 45000
    generator.update_feature_online(btc_symbol, TradeTick(
        symbol=btc_symbol, trade_id=1, price=Price(Decimal("45000.0"), btc_symbol),
        quantity=Quantity(Decimal("1.5"), "BTC"), timestamp=ExchangeTimestamp(100), side=Side.BUY
    ))

    # 2. Sell: qty 0.5, price 44990
    generator.update_feature_online(btc_symbol, TradeTick(
        symbol=btc_symbol, trade_id=2, price=Price(Decimal("44990.0"), btc_symbol),
        quantity=Quantity(Decimal("0.5"), "BTC"), timestamp=ExchangeTimestamp(200), side=Side.SELL
    ))

    # 3. Buy: qty 2.0, price 45005
    last_dict = generator.update_feature_online(btc_symbol, TradeTick(
        symbol=btc_symbol, trade_id=3, price=Price(Decimal("45005.0"), btc_symbol),
        quantity=Quantity(Decimal("2.0"), "BTC"), timestamp=ExchangeTimestamp(300), side=Side.BUY
    ))

    # Net Delta: buy (1.5 + 2.0 = 3.5) - sell (0.5) = 3.0
    assert Decimal(last_dict["delta"]) == Decimal("3.0")
    # CVD: buy (+1.5) -> sell (-0.5) -> buy (+2.0) = 3.0
    assert Decimal(last_dict["cumulative_delta"]) == Decimal("3.0")


@pytest.mark.unit
def test_feature_generation_sweep_detection(btc_symbol, initial_snapshot):
    """Verify that a sweep event is detected when price penetrates the range and mid-price rejects."""
    from domain.value_objects import Price, Quantity
    generator = NGLSFeatureGenerator(btc_symbol)
    generator.update_feature_online(btc_symbol, initial_snapshot)

    # Establish swing high range using 10 trades around 45010.0
    for i in range(10):
        generator.update_feature_online(btc_symbol, TradeTick(
            symbol=btc_symbol, trade_id=i+1, price=Price(Decimal("45010.0"), btc_symbol),
            quantity=Quantity(Decimal("1.0"), "BTC"), timestamp=ExchangeTimestamp(100 + i*10), side=Side.BUY
        ))

    # Penetrating tick to 45020 (above swing high of 45000)
    # The L2 book ask is still at 45010 (meaning mid-price is (45000+45010)/2 = 45005)
    # Since penetration was to 45020 (>= prev_high 45000) and mid-price is 45005 (< prev_high 45000), it's a sweep!
    sweep_dict = generator.update_feature_online(btc_symbol, TradeTick(
        symbol=btc_symbol, trade_id=99, price=Price(Decimal("45020.0"), btc_symbol),
        quantity=Quantity(Decimal("5.0"), "BTC"), timestamp=ExchangeTimestamp(200), side=Side.BUY
    ))

    assert sweep_dict["is_sweep"] is True
    assert Decimal(sweep_dict["sweep_level_price"]) == Decimal("45020.0")
    assert Decimal(sweep_dict["sweep_volume_consumed"]) == Decimal("5.0")
    assert Decimal(sweep_dict["sweep_rejection_ratio"]) == Decimal("0.5")


@pytest.mark.unit
def test_feature_generation_absorption_detection(btc_symbol):
    """Verify high-volume, low-price movement triggers absorption."""
    from domain.value_objects import Price, Quantity
    generator = NGLSFeatureGenerator(btc_symbol)

    # Send 10 trades with high volume (qty=2.0 each, total=20.0 > 10.0 threshold)
    # within a narrow price range (45000.0 to 45001.0, range=1.0 < 5.0 threshold)
    for i in range(10):
        last_dict = generator.update_feature_online(btc_symbol, TradeTick(
            symbol=btc_symbol, trade_id=i+1, price=Price(Decimal(f"45000.{i}"), btc_symbol),
            quantity=Quantity(Decimal("2.0"), "BTC"), timestamp=ExchangeTimestamp(100 + i*10), side=Side.BUY
        ))

    assert last_dict["is_absorption"] is True
    assert Decimal(last_dict["absorption_volume"]) == Decimal("20.0")
    assert Decimal(last_dict["absorption_price_range"]) == Decimal("0.9")


@pytest.mark.unit
def test_deterministic_replay_features(btc_symbol, initial_snapshot):
    """Verify that replaying identical tick/snapshot sequences yields byte-identical features."""
    from domain.value_objects import Price, Quantity
    gen_a = NGLSFeatureGenerator(btc_symbol)
    gen_b = NGLSFeatureGenerator(btc_symbol)

    events = [
        initial_snapshot,
        TradeTick(symbol=btc_symbol, trade_id=1, price=Price(Decimal("45002.0"), btc_symbol),
                  quantity=Quantity(Decimal("0.5"), "BTC"), timestamp=ExchangeTimestamp(100), side=Side.BUY),
        TradeTick(symbol=btc_symbol, trade_id=2, price=Price(Decimal("44998.0"), btc_symbol),
                  quantity=Quantity(Decimal("1.0"), "BTC"), timestamp=ExchangeTimestamp(200), side=Side.SELL)
    ]

    results_a = []
    results_b = []

    for event in events:
        results_a.append(gen_a.update_feature_online(btc_symbol, event))
        results_b.append(gen_b.update_feature_online(btc_symbol, event))

    assert results_a == results_b


@pytest.mark.unit
def test_multi_symbol_isolation(btc_symbol, eth_symbol, initial_snapshot):
    """Verify that updating features for one symbol does not affect another."""
    from domain.value_objects import Price, Quantity
    btc_gen = NGLSFeatureGenerator(btc_symbol)
    eth_gen = NGLSFeatureGenerator(eth_symbol)

    btc_gen.update_feature_online(btc_symbol, initial_snapshot)

    eth_snapshot = OrderBookSnapshot(
        symbol=eth_symbol,
        timestamp=ExchangeTimestamp(1700000000000),
        bids=[OrderBookLevel(Price(Decimal("3000.0"), eth_symbol), Quantity(Decimal("10.0"), "ETH"))],
        asks=[OrderBookLevel(Price(Decimal("3005.0"), eth_symbol), Quantity(Decimal("12.0"), "ETH"))],
        sequence_id=200
    )
    eth_gen.update_feature_online(eth_symbol, eth_snapshot)

    btc_snap = btc_gen.get_feature_snapshot()
    eth_snap = eth_gen.get_feature_snapshot()

    assert btc_snap.symbol == btc_symbol
    assert eth_snap.symbol == eth_symbol
    assert btc_snap.spread == Decimal("10.0")
    assert eth_snap.spread == Decimal("5.0")
