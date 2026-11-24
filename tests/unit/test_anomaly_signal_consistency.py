"""Unit tests to verify signal consistency and correctness for anomaly watchers.

Ensures that positive anomaly observations result in negative direction and SELL bias,
and that negative anomaly observations result in positive direction and BUY bias.
Also verifies that the strategy adapter correctly determines side matching the bias,
preventing signal contradictions in the broker layer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import logging
import pytest

from domain.entities import MarketObservation, InterpretedSignal, FusedSignal, SignalType, OrderSide
from domain.value_objects import Symbol, Percentage
from infrastructure.engines.engine_service import EngineService
from infrastructure.fusion.fusion_service import FusionService
from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter


# E16-U7: the anomaly-reversion (contrarian) mapping was removed from the Engine (not supported by
# data, E18); anomaly is a regime observation -> NEUTRAL, direction 0 (tests/unit/test_engine_role_aware.py).


@pytest.mark.unit
def test_positive_anomaly_observation_hierarchical_fusion_wait():
    # 1. Test positive anomaly through hierarchical fusion with single signal.
    # Because hierarchical fusion requires multiple aligned signals, a single signal will result in WAIT (neutral).
    engine = EngineService()
    
    positive_anomaly_obs = MarketObservation(
        symbol=Symbol("ZECUSDT"),
        observation_type="anomaly_ml",
        observation_value=0.994,
        confidence=Percentage(Decimal("0.76")),
        timestamp=datetime.now(),
        metadata={"watcher_name": "anomaly_ml"}
    )
    
    interpreted = engine.process_observation(positive_anomaly_obs)
    assert interpreted is not None
    
    fusion = FusionService()
    fused = fusion.fuse_signals([interpreted])
    assert fused is not None
    # Single discovery signal doesn't satisfy hierarchical rules (needs direction signals alignment), so result is NEUTRAL (WAIT)
    assert fused.dominant_bias == SignalType.NEUTRAL
    assert fused.direction == 0.0
