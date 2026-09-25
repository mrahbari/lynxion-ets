"""Characterize existing live queue ordering without orders or network."""

from datetime import datetime, timezone
import threading
from types import SimpleNamespace

from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator


T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def first_processed(symbols, monkeypatch):
    import infrastructure.orchestrators.auto_detection_orchestrator as owner_module

    monkeypatch.setattr(owner_module.time, "sleep", lambda _: None)
    seen = []
    owner = SimpleNamespace(
        is_running=True,
        opportunity_queue=[SimpleNamespace(symbol=SimpleNamespace(value=symbol),
                                           timestamp=T) for symbol in symbols],
        _opportunity_queue_lock=threading.RLock(),
        logger=SimpleNamespace(info=lambda *args: None, debug=lambda *args: None,
                               error=lambda *args: None, comprehensive_mode=False),
        active_trades={},
        _get_cooldown_gate=lambda: SimpleNamespace(
            is_symbol_allowed=lambda symbol: (True, "")),
    )

    def execute(intent):
        seen.append(intent.symbol.value)
        owner.is_running = False

    owner._execute_strategy_for_opportunity = execute
    AutoDetectionOrchestrator._opportunity_processing_loop(owner)
    return seen


def test_same_event_time_queue_delivery_order_changes_first_processed_symbol(monkeypatch):
    assert first_processed(["BTCUSDT", "ETHUSDT"], monkeypatch) == ["BTCUSDT"]
    assert first_processed(["ETHUSDT", "BTCUSDT"], monkeypatch) == ["ETHUSDT"]
