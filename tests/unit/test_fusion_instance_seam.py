from datetime import datetime, timezone

from domain.value_objects import Symbol
from infrastructure.fusion.fusion_service import FusionService
from infrastructure.fusion.hierarchical.hierarchical_fusion_service import (
    HierarchicalFusionService, hierarchical_fusion_service,
)
from infrastructure.messaging.clock import ReplayClock


def test_live_default_keeps_original_hierarchical_service():
    assert FusionService().hierarchical_service is hierarchical_fusion_service


def test_two_explicit_fusion_scopes_do_not_share_symbol_state_or_clock():
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock_a = ReplayClock(instant)
    clock_b = ReplayClock(instant)
    a = FusionService(hierarchical_service=HierarchicalFusionService(clock=clock_a), clock=clock_a)
    b = FusionService(hierarchical_service=HierarchicalFusionService(clock=clock_b), clock=clock_b)
    assert a.hierarchical_service is not b.hierarchical_service
    assert a.hierarchical_service.symbol_manager is not b.hierarchical_service.symbol_manager
    assert a.hierarchical_service.symbol_manager.state_machine is not b.hierarchical_service.symbol_manager.state_machine
    btc = Symbol("BTCUSDT")
    eth = Symbol("ETHUSDT")
    a.hierarchical_service.symbol_manager.process_discovery(btc)
    assert b.hierarchical_service.symbol_manager.state_machine.get_state(btc) is None
    assert a.hierarchical_service.symbol_manager.state_machine.get_state(eth) is None
    status = a.hierarchical_service.symbol_manager.get_symbol_status(btc)
    assert status["state_history"][0]["timestamp"] == instant.isoformat()


def test_neutral_output_uses_supplied_event_clock():
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    hierarchy = HierarchicalFusionService(clock=ReplayClock(instant))
    signal = hierarchy._create_neutral_fused_signal(Symbol("BTCUSDT"), "RISK_OFF", 0.5, "test")
    assert signal.timestamp == instant
