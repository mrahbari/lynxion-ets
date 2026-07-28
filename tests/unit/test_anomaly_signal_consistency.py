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


@pytest.mark.unit
def test_positive_anomaly_observation_reversion_sell_standard_fusion():
    # 1. Test positive anomaly -> SELL interpreted signal with negative direction
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
    assert interpreted.signal_type == SignalType.SELL
    # The direction must be negative for positive anomaly
    assert interpreted.direction == -0.994
    assert interpreted.strength > 0.0
    
    # Force standard fusion by clearing source_watcher
    interpreted.source_watcher = None
    
    # 2. Trace fusion (single signal case)
    fusion = FusionService()
    fused = fusion.fuse_signals([interpreted])
    assert fused is not None
    assert fused.dominant_bias == SignalType.SELL
    assert fused.direction == -0.994
    
    # 3. Trace strategy adapter determine_side
    strategy = MeanReversionStrategyAdapter()
    strategy.logger = logging.getLogger("test")
    
    side = strategy._determine_side(fused)
    assert side == OrderSide.SELL


@pytest.mark.unit
def test_negative_anomaly_observation_reversion_buy_standard_fusion():
    # 1. Test negative anomaly -> BUY interpreted signal with positive direction
    engine = EngineService()
    
    negative_anomaly_obs = MarketObservation(
        symbol=Symbol("ZECUSDT"),
        observation_type="anomaly_ml",
        observation_value=-0.994,
        confidence=Percentage(Decimal("0.76")),
        timestamp=datetime.now(),
        metadata={"watcher_name": "anomaly_ml"}
    )
    
    interpreted = engine.process_observation(negative_anomaly_obs)
    assert interpreted is not None
    assert interpreted.signal_type == SignalType.BUY
    # The direction must be positive for negative anomaly
    assert interpreted.direction == 0.994
    
    # Force standard fusion by clearing source_watcher
    interpreted.source_watcher = None
    
    # 2. Trace fusion (single signal case)
    fusion = FusionService()
    fused = fusion.fuse_signals([interpreted])
    assert fused is not None
    assert fused.dominant_bias == SignalType.BUY
    assert fused.direction == 0.994
    
    # 3. Trace strategy adapter determine_side
    strategy = MeanReversionStrategyAdapter()
    strategy.logger = logging.getLogger("test")
    
    side = strategy._determine_side(fused)
    assert side == OrderSide.BUY


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
