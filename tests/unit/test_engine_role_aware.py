"""E16-U7: the Engine translates by watcher role; only direction watchers carry a side."""
from datetime import datetime
from decimal import Decimal

import pytest

from domain.entities import MarketObservation, SignalType
from domain.value_objects import Percentage, Symbol
from infrastructure.engines.engine_service import EngineService

B, S, N = SignalType.BUY, SignalType.SELL, SignalType.NEUTRAL


def obs(label, value=0.8, watcher=None, role=None):
    meta = {}
    if watcher:
        meta["watcher_name"] = watcher
    if role:
        meta["contract"] = {"role": role}
    return MarketObservation(symbol=Symbol("BTCUSDT"), observation_type=label, observation_value=value,
                             confidence=Percentage(Decimal("0.7")), timestamp=datetime.now(), metadata=meta)


@pytest.mark.parametrize("label,value,watcher,expected,direction", [
    ("trend_positive", 0.6, "TrendMTFWatcher", B, 1.0),
    ("trend_negative", -0.6, "TrendMTFWatcher", S, -1.0),
    ("trend_neutral", 0.0, "TrendMTFWatcher", N, 0.0),
    ("market_pulse_bullish_strong", 2.1, "MarketPulseWatcher", B, 1.0),
    ("market_pulse_bearish_oversold_caution", -0.5, "MarketPulseWatcher", N, 0.0),
    ("market_pulse_neutral_low_momentum", 0.0, "MarketPulseWatcher", N, 0.0),
    ("candle_reversal_bullish_emerging", 0.5, None, B, 1.0),          # watcher guessed from label
    ("order_flow_sell_pressure", -0.4, "OrderFlowWSWatcher", S, -1.0),
    ("volatility_normal", 0.0, "VolatilityWatcher", N, 0.0),           # was HOLD
    ("volatility_expansion", 0.9, "VolatilityWatcher", N, 0.0),        # was direction +0.5
    ("liquidity_normal", 0.0, "LiquidityWatcher", N, 0.0),             # was HOLD
    ("liquidity_high", 0.9, "LiquidityWatcher", N, 0.0),               # was direction +0.9
    ("anomaly_positive", 0.9, "AnomalyMLWatcher", N, 0.0),             # was contrarian SELL
    ("anomaly_negative", -0.9, "AnomalyMLWatcher", N, 0.0),            # was contrarian BUY
    ("funding_rate_positive", 0.8, "FundingRateWatcher", N, 0.0),      # was contrarian SELL
])
def test_every_live_label(label, value, watcher, expected, direction):
    s = EngineService().process_observation(obs(label, value, watcher))
    assert s.signal_type is expected and s.direction == direction
    assert s.metadata["engine_role"] in ("direction", "regime", "positioning", "execution")


def test_declared_contract_role_wins_over_fallback():
    s = EngineService().process_observation(obs("trend_positive", 0.6, "TrendMTFWatcher", role="regime"))
    assert s.signal_type is N and s.direction == 0.0 and s.metadata["engine_role"] == "regime"
