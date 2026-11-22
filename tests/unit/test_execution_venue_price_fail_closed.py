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


def _intent(name):
    return N(symbol=N(value="SOLUSDT"), strategy_name=name, side=N(name="BUY"),
             intent_confidence=N(value=0.9))


def test_strategy_allowlist_rejects_other_strategies(monkeypatch):
    m = _m(); m.is_running = True; removed = []
    m._remove_pending_execution_intent = removed.append
    m._claim_execution_intent = lambda i: (_ for _ in ()).throw(AssertionError("must not reach claim"))
    monkeypatch.setenv("STRATEGY_ALLOWLIST", "trend_following, VWAPReversal")
    r = m._execute_trade_from_intent(_intent("MeanReversion"))
    assert r["error"] == "STRATEGY_NOT_ALLOWLISTED:MeanReversion" and len(removed) == 1


def test_allowlisted_strategy_passes_the_gate(monkeypatch):
    m = _m(); m.is_running = True
    m._claim_execution_intent = lambda i: False   # stop right after the gate
    monkeypatch.setenv("STRATEGY_ALLOWLIST", "trend_following,vwapreversal")
    assert m._execute_trade_from_intent(_intent("VWAPReversal"))["error"] == "DUPLICATE_LOGICAL_INTENT"
    monkeypatch.delenv("STRATEGY_ALLOWLIST")
    assert m._execute_trade_from_intent(_intent("MeanReversion"))["error"] == "DUPLICATE_LOGICAL_INTENT"


def test_allowlist_matches_registry_adapter_and_config_names(monkeypatch):
    from infrastructure.strategies.strategy_config import StrategyConfig
    monkeypatch.setenv("STRATEGY_ALLOWLIST", "trend_following,TrendFollow,VWAPReversal,OIFootprint")
    for name in ("trend_following", "TrendFollow", "vwap_reversal", "VWAPReversal", "VWAP_REVERSAL", "oi_footprint", "OIFootprint"):
        assert StrategyConfig.get_strategy_enabled(name), name
    for name in ("crypto_breakout", "Breakout", "mean_reversion", "SWEEP_SCALPER"):
        assert not StrategyConfig.get_strategy_enabled(name), name
    monkeypatch.setenv("STRATEGY_ALLOWLIST", "")
    assert StrategyConfig.get_strategy_enabled("crypto_breakout")
