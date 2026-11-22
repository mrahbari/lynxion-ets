"""Watchers must see each closed bar exactly once (live fed the same 30-bar window every cycle)."""
import time
from types import SimpleNamespace

from infrastructure.watchers.monitoring_analysis_service import MonitoringAnalysisService


class _Rec:
    def __init__(self):
        self.seen = []

    def update_data(self, data):
        self.seen.append(data)


def _svc(bars):
    svc = object.__new__(MonitoringAnalysisService)
    svc.logger = SimpleNamespace(warning=lambda *a, **k: None, error=lambda *a, **k: None,
                                 debug=lambda *a, **k: None)
    rec = _Rec()
    svc.watchers = {"BTCUSDT": {"rec": rec}}
    svc._funding_payload = lambda sym: None
    calls = []
    svc.market_data_repo = SimpleNamespace(
        get_historical_data=lambda symbol, period, timeframe: (calls.append(period), bars())[1])
    return svc, rec, calls


def _bars(now, n=30):
    start = int(now // 60) * 60 - (n - 1) * 60          # last bar is still forming
    return [{"timestamp": start + 60 * i, "open": i + 1, "high": i + 2, "low": i + 0.5, "close": i + 1, "volume": 1}
            for i in range(n)]


def test_each_closed_bar_is_fed_once_and_forming_bar_never():
    now = time.time()
    svc, rec, calls = _svc(lambda: _bars(now))
    sym = SimpleNamespace(value="BTCUSDT")
    svc._update_watchers_with_market_data(sym)
    svc._update_watchers_with_market_data(sym)
    closes = [d["close"] for d in rec.seen]
    assert closes == list(range(1, 30))                   # 29 closed bars, once each, in order
    assert all("candle" in d and d["candle"]["close"] == d["close"] for d in rec.seen)
    assert calls == ["6h", "30m"]                        # warm-up once, then incremental


def test_funding_is_forwarded_once():
    now = time.time()
    svc, rec, _ = _svc(lambda: _bars(now, 3))
    payloads = iter([{"funding_rate": 0.0001}, None])
    svc._funding_payload = lambda sym: next(payloads)
    sym = SimpleNamespace(value="BTCUSDT")
    svc._update_watchers_with_market_data(sym)
    svc._update_watchers_with_market_data(sym)
    assert [d for d in rec.seen if "funding_rate" in d] == [{"funding_rate": 0.0001}]
