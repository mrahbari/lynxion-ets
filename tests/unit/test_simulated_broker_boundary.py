"""The replay broker has deterministic local order state and no risk logic."""

from types import SimpleNamespace

from infrastructure.replay.simulated_broker import SimulatedBrokerAdapter


def test_simulated_broker_is_local_deterministic_and_does_not_assume_fill():
    order = SimpleNamespace(symbol="BTCUSDT", quantity=2.0)
    first, second = SimulatedBrokerAdapter(), SimulatedBrokerAdapter()
    assert not hasattr(first, "connect")
    assert not hasattr(first, "credentials")
    assert not hasattr(first, "fetch_order_book")
    assert first.place_order(order) == "REPLAY-00000001"
    assert second.place_order(order) == "REPLAY-00000001"
    assert first.get_position("BTCUSDT") is None
    assert len(first.get_open_orders("BTCUSDT")) == 1
    assert first.get_open_orders("ETHUSDT") == []
    assert first.cancel_order("REPLAY-00000001")
    assert first.get_open_orders("BTCUSDT") == []
    assert second.get_order_status("REPLAY-00000001") == "ACCEPTED"
