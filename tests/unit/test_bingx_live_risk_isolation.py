"""Real-account entry must not inherit VST-only risk limits."""

from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


def test_live_entry_denied_before_broker_or_risk_access():
    broker = object.__new__(_BingXBroker)
    broker.testnet = False
    broker._make_request = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("authenticated request must not occur")
    )

    allowed, reason = broker._assert_entry_admission(None)

    assert not allowed
    assert "live risk policy is not configured" in reason
