"""Order flows must not be starved by the BingX request budget or uncached symbol lookups."""
from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


def test_bingx_budget_supports_a_full_order_flow_quickly():
    from shared.rate_limiter import GlobalRateLimiter
    lim = GlobalRateLimiter().get_limiter("bingx")
    per_second = lim.max_requests / lim.time_window
    assert per_second >= 1.0   # a 10-call entry flow completes in seconds, not minutes


def test_available_symbols_use_swap_contracts_and_cache():
    calls = []
    b = _BingXBroker.__new__(_BingXBroker)
    import logging; b.logger = logging.getLogger("t")

    def req(method, endpoint, **kw):
        calls.append(endpoint)
        return {"code": 0, "data": [{"symbol": "BTC-USDT", "status": 1}, {"symbol": "OLD-USDT", "status": 0}]}
    b._make_request = req
    assert b.get_available_symbols() == {"BTCUSDT"}
    assert b.get_available_symbols() == {"BTCUSDT"}
    assert calls == ["/openApi/swap/v2/quote/contracts"]
