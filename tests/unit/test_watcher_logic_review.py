import pytest
"""Watcher logic review (2026-11-23): each watcher does the job its name says."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import numpy as np

from domain.entities import MarketObservation, SignalType
from domain.value_objects import Percentage, Symbol
from infrastructure.engines.engine_service import EngineService
from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter
from infrastructure.watchers.adapters.volatility import VolatilityWatcher

S = Symbol("BTCUSDT")
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _obs(kind, value=0.0):
    return MarketObservation(symbol=S, observation_type=kind, observation_value=value,
                             confidence=Percentage(Decimal("0.7")), timestamp=T0)


def test_anomaly_is_rare_on_ordinary_bars_and_fires_on_a_shock():
    rng = np.random.default_rng(3)
    w = AnomalyMLWatcher("anomaly_ml", "BTCUSDT")
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, 600)))
    flagged = 0
    for p in px:
        w.update_data({"close": float(p), "volume": 10.0})
        o = w.analyze(S)
        flagged += o is not None and o.observation_type != "anomaly_normal"
    assert flagged <= 6                      # old score flagged most bars
    w.update_data({"close": float(px[-1] * 1.02), "volume": 50.0})
    o = w.analyze(S)
    assert o.observation_type == "anomaly_positive" and float(o.confidence.value) >= 0.70


def test_volatility_regime_compares_last_hour_with_baseline():
    rng = np.random.default_rng(5)
    w = VolatilityWatcher("volatility", "BTCUSDT")
    px = list(100 * np.exp(np.cumsum(rng.normal(0, 0.001, 1400))))
    px += list(px[-1] * np.exp(np.cumsum(rng.normal(0, 0.004, 60))))
    for p in px:
        w.update_data({"close": float(p), "high": float(p), "low": float(p)})
    o = w.analyze(S)
    assert o.observation_type == "volatility_expansion" and o.metadata["vol_ratio"] > 1.5


def test_engine_reads_volatility_as_non_directional_and_pulse_by_side():
    e = EngineService()
    assert e.process_observation(_obs("volatility_expansion", 0.9)).signal_type is SignalType.NEUTRAL
    assert e.process_observation(_obs("market_pulse_bullish_strong", 0.0)).signal_type is SignalType.BUY
    assert e.process_observation(_obs("market_pulse_bearish_strong", 0.0)).signal_type is SignalType.SELL
    assert e.process_observation(_obs("market_pulse_bullish_overbought_caution", 0.5)).signal_type is SignalType.NEUTRAL


def test_funding_extremes_pass_the_gate_and_normal_does_not():
    w = FundingRateWatcher("funding_rate", "BTCUSDT")
    w.update_data({"funding_rate": 0.0001})
    assert float(w.analyze(S).confidence.value) < 0.6
    w.update_data({"funding_rate": 0.0015})
    o = w.analyze(S)
    assert o.observation_type == "funding_rate_extremely_positive" and float(o.confidence.value) >= 0.6


def _candle_watcher():
    return HistoricalCandleWatcherAdapter(SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True)),
                                          "historical_candle", "BTCUSDT")


def _feed_15m(w, bars):
    """Feed each 15m OHLC as 15 one-minute candles."""
    for k, (o, h, l, c) in enumerate(bars):
        for m in range(15):
            t = T0 + timedelta(minutes=15 * k + m)
            px = o if m == 0 else c
            w.update_data({"candle": {"open": px, "high": h if m == 7 else max(o, c), "low": l if m == 8 else min(o, c),
                                      "close": c if m == 14 else px, "volume": 1, "close_time": t + timedelta(minutes=1)}})


def test_hammer_after_downtrend_is_bullish_and_needs_closed_15m_candles():
    w = _candle_watcher()
    down = [(100 - k, 100.5 - k, 98.5 - k, 99 - k) for k in range(20)]
    _feed_15m(w, down)
    assert w.analyze(S).observation_type == "candle_neutral"
    last = down[-1][3]
    _feed_15m_tail = [(last, last + 0.1, last - 4.0, last + 0.05)]   # long lower shadow, tiny body
    for m in range(15):
        t = T0 + timedelta(minutes=15 * 20 + m)
        o, h, l, c = _feed_15m_tail[0]
        w.update_data({"candle": {"open": o if m == 0 else c, "high": h, "low": l if m == 5 else c, "close": c,
                                  "volume": 1, "close_time": t + timedelta(minutes=1)}})
        if m < 14:
            assert w.analyze(S).observation_type == "candle_neutral"   # still forming: not used
    o = w.analyze(S)
    assert o.observation_type == "candle_reversal_bullish"
    assert EngineService().process_observation(o).signal_type is SignalType.BUY


def test_funding_rate_is_normalised_to_8h_before_thresholds():
    from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
    w4 = FundingRateWatcher("funding_rate", "ENAUSDT")
    w4.update_data({"funding_rate": 0.0003, "funding_interval_hours": 4})    # = 0.06 % per 8 h
    obs = w4.analyze(w4.symbol)
    assert obs.observation_type == "funding_rate_positive"
    assert obs.metadata["current_funding_rate"] == pytest.approx(0.0006)
    w8 = FundingRateWatcher("funding_rate", "BTCUSDT")
    w8.update_data({"funding_rate": 0.0003, "funding_interval_hours": 8})
    assert w8.analyze(w8.symbol).observation_type == "funding_rate_normal"
    legacy = FundingRateWatcher("funding_rate", "BTCUSDT")
    legacy.update_data({"funding_rate": 0.0003})                              # no interval: unchanged
    assert legacy.analyze(legacy.symbol).metadata["current_funding_rate"] == pytest.approx(0.0003)


def _pulse(closes):
    from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
    w = MarketPulseWatcher("market_pulse", "BTCUSDT")
    for c in closes:
        w.update_data({"candle": {"open": c, "high": c, "low": c, "close": c, "volume": 1}})
    return w.analyze(w.symbol)


def test_market_pulse_random_walk_is_mostly_neutral():
    import numpy as np
    rng = np.random.default_rng(5)
    labels = [_pulse(100 * np.exp(np.cumsum(rng.normal(0, 0.0008, 75)))).observation_type for _ in range(1500)]
    assert sum(lbl != "market_pulse_neutral_low_momentum" for lbl in labels) / len(labels) < 0.10


def test_market_pulse_flags_a_real_15_minute_move_by_side():
    import numpy as np
    rng = np.random.default_rng(6)
    base = list(100 * np.exp(np.cumsum(rng.normal(0, 0.0005, 60))))
    up = base + [base[-1] * np.exp(0.002 * k) for k in range(1, 16)]           # +3 % in 15 min
    down = base + [base[-1] * np.exp(-0.002 * k) for k in range(1, 16)]
    assert "bullish" in _pulse(up).observation_type
    assert "bearish" in _pulse(down).observation_type
    assert _pulse(base[:40]) is None                                         # warm-up: 61 closes needed


def test_orderflow_watcher_receives_new_public_trades_once():
    from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
    from infrastructure.watchers.monitoring_analysis_service import MonitoringAnalysisService
    svc = object.__new__(MonitoringAnalysisService)
    import logging
    svc.logger = logging.getLogger("t")
    w = OrderFlowWSWatcher("orderflow_ws", "BTCUSDT")
    svc.watchers = {"BTCUSDT": {"orderflow_ws": w}}
    trades = [{"time": 1, "price": "100", "qty": "3", "isBuyerMaker": False},
              {"time": 2, "price": "100", "qty": "1", "isBuyerMaker": True}]
    assert svc._feed_trades("BTCUSDT", trades) == 2
    assert svc._feed_trades("BTCUSDT", trades) == 0                  # already fed
    assert w.order_flow_imbalance_history[-1] == pytest.approx(0.5)  # (3 - 1) / 4
    assert w.analyze(w.symbol) is not None


def test_every_live_watcher_declares_a_contract_and_stamps_it():
    from infrastructure.watchers.adapters.volatility import VolatilityWatcher
    from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
    from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
    from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
    from infrastructure.watchers.adapters.liquidity import LiquidityWatcher
    from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
    from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter
    from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
    for cls in (VolatilityWatcher, TrendMTFWatcher, FundingRateWatcher, MarketPulseWatcher, LiquidityWatcher,
                OrderFlowWSWatcher, HistoricalCandleWatcherAdapter, AnomalyMLWatcher):
        assert cls.ROLE in {"regime", "direction", "positioning", "execution"} and cls.HORIZON and cls.CLAIM
    w = FundingRateWatcher("funding_rate", "BTCUSDT")
    w._last_bar_close = 1_700_000_060
    w.update_data({"funding_rate": 0.0001, "funding_interval_hours": 8})
    obs = w.analyze(w.symbol)
    assert obs.metadata["contract"]["role"] == "positioning"
    assert obs.metadata["as_of_bar_close"] == 1_700_000_060
