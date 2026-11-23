"""E15-F1: fusion over the latest state of all watchers of a symbol."""
from datetime import datetime
from decimal import Decimal

import pytest

from domain.entities import InterpretedSignal, SignalType
from domain.value_objects import Percentage, Symbol
from infrastructure.fusion.symbol_state_fusion import SymbolStateFusion


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def now(self):
        return datetime.fromtimestamp(self.t)


def sig(watcher, obs_type, conf=0.7, role=None, sym="BTCUSDT"):
    meta = {"watcher_name": watcher, "observation_type": obs_type}
    if role:
        meta["contract"] = {"role": role, "validated": None}
    return InterpretedSignal(symbol=Symbol(sym), signal_type=SignalType.NEUTRAL, direction=0.0, strength=0.0,
                             confidence=Percentage(Decimal(str(conf))), timestamp=datetime.now(),
                             source_watcher=watcher, metadata=meta)


@pytest.fixture
def fx():
    c = Clock()
    return SymbolStateFusion(clock=c), c


def test_fuses_state_of_several_watchers_not_only_the_triggering_one(fx):
    f, _ = fx
    f.update(sig("trend_mtf", "trend_positive", 0.6))
    out = f.update(sig("market_pulse", "market_pulse_bullish_strong", 0.7))
    assert out.dominant_bias is SignalType.BUY and out.direction == pytest.approx(1.0)
    assert set(out.metadata["contributors"]) == {"trend_mtf", "market_pulse"}
    assert out.regime_context == "bullish_trending"


def test_conflicting_directions_cancel_and_neutral_votes_dilute(fx):
    f, _ = fx
    f.update(sig("trend_mtf", "trend_positive", 0.6))
    out = f.update(sig("market_pulse", "market_pulse_bearish_strong", 0.6))
    assert out.dominant_bias is SignalType.NEUTRAL and out.confidence.value == 0
    out = f.update(sig("historical_candle", "candle_neutral", 0.3))
    assert out.metadata["direction_voters"]["historical_candle"] == 0


def test_stale_state_expires(fx):
    f, c = fx
    f.update(sig("trend_mtf", "trend_positive", 0.6))
    c.t += 301
    out = f.update(sig("volatility", "volatility_normal", 0.3))
    assert "trend_mtf" not in out.metadata["contributors"] and out.dominant_bias is SignalType.NEUTRAL


def test_liquidity_is_execution_not_direction_and_contract_role_wins(fx):
    f, _ = fx
    out = f.update(sig("liquidity", "liquidity_high", 0.9))
    assert out.metadata["roles"]["liquidity"] == "execution"
    assert "liquidity" not in out.metadata["direction_voters"]
    out = f.update(sig("custom", "custom_bullish", 0.9, role="regime"))
    assert "custom" not in out.metadata["direction_voters"]


def test_regime_uses_validated_volatility_and_anomaly(fx):
    f, _ = fx
    assert f.update(sig("volatility", "volatility_compression", 0.92)).regime_context == "ranging"
    assert f.update(sig("volatility", "volatility_expansion", 0.85)).regime_context == "volatile"
    f.update(sig("volatility", "volatility_normal", 0.3))
    assert f.update(sig("anomaly_ml", "anomaly_positive", 0.74)).regime_context == "volatile"


def test_symbols_are_independent_and_class_names_are_mapped(fx):
    f, _ = fx
    f.update(sig("TrendMTFWatcher", "trend_positive", 0.6, sym="ETHUSDT"))
    out = f.update(sig("volatility", "volatility_normal", 0.3, sym="BTCUSDT"))
    assert "trend_mtf" not in out.metadata["contributors"]
    out = f.update(sig("volatility", "volatility_normal", 0.3, sym="ETHUSDT"))
    assert "trend_mtf" in out.metadata["contributors"]


def test_fusion_service_mode_switch(monkeypatch):
    from infrastructure.fusion.fusion_service import FusionService
    out = FusionService(mode="state").fuse_signals([sig("volatility", "volatility_expansion", 0.85, sym="SOLUSDT")])
    assert out.metadata.get("state_fusion") is True
    monkeypatch.delenv("FUSION_MODE", raising=False)
    out = FusionService().fuse_signals([sig("volatility", "volatility_expansion", 0.85, sym="SOLUSDT")])
    assert out is None or not (out.metadata or {}).get("state_fusion")
