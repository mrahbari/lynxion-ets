"""Order sizing must use the execution venue's live price; never stale CSV or fabricated prices."""
import logging
from types import SimpleNamespace as N
from unittest.mock import patch

from infrastructure.orchestrators._auto_detection_execution import _AutoDetectionExecutionMixin as M


def _m(testnet=True):
    m = M(); m.logger = logging.getLogger("t"); m._settings = N(broker=N(bingx_testnet=testnet))
    return m


class _R:
    def __init__(self, payload): self._p = payload
    def json(self): return self._p


def test_uses_vst_host_and_formats_symbol():
    with patch("requests.get", return_value=_R({"code": 0, "data": {"price": "123.5"}})) as g:
        assert _m()._venue_price(N(value="SOLUSDT")) == 123.5
    url, kw = g.call_args[0][0], g.call_args[1]
    assert url.startswith("https://open-api-vst.bingx.com") and kw["params"] == {"symbol": "SOL-USDT"}


def test_live_host_when_not_testnet():
    with patch("requests.get", return_value=_R({"code": 0, "data": {"price": "1"}})) as g:
        _m(testnet=False)._venue_price(N(value="BTCUSDT"))
    assert g.call_args[0][0].startswith("https://open-api.bingx.com")


def test_error_or_bad_price_returns_none():
    for payload in ({"code": 100400, "data": {}}, {"code": 0, "data": {"price": "0"}}, {"code": 0, "data": {"price": "nan"}}):
        with patch("requests.get", return_value=_R(payload)):
            assert _m()._venue_price(N(value="BTCUSDT")) is None
    with patch("requests.get", side_effect=TimeoutError):
        assert _m()._venue_price(N(value="BTCUSDT")) is None


def test_no_fabricated_price_fallback_left_in_execution_path():
    import inspect
    from infrastructure.orchestrators import _auto_detection_execution as mod
    src = inspect.getsource(mod)
    assert "random.uniform" not in src and "45000.0" not in src
