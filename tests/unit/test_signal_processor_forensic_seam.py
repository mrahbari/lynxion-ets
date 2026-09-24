from datetime import datetime, timezone
from types import SimpleNamespace

from infrastructure.messaging.event_system import EventRouter, EventType, SignalEvent, SignalProcessor


class RecordingSink:
    def __init__(self):
        self.engine_calls = []
        self.fusion_calls = []

    def log_engine_interpretation(self, **kwargs):
        self.engine_calls.append(kwargs)

    def log_fusion_result(self, **kwargs):
        self.fusion_calls.append(kwargs)


class RecordingRouter(EventRouter):
    def __init__(self):
        super().__init__()
        self.interpreted = []
        self.fused = []

    def publish_interpreted_signal(self, signal, **kwargs):
        self.interpreted.append((signal, kwargs))

    def publish_fused_signal(self, signal, **kwargs):
        self.fused.append((signal, kwargs))


def test_explicit_forensic_sink_receives_subscribed_flow_without_global_log(monkeypatch):
    import infrastructure.logging.forensic_logger as module

    class ForbiddenGlobalSink:
        def log_engine_interpretation(self, **kwargs):
            raise AssertionError("global forensic sink used")

        def log_fusion_result(self, **kwargs):
            raise AssertionError("global forensic sink used")

    monkeypatch.setattr(module, "forensic_logger", ForbiddenGlobalSink())
    router = RecordingRouter()
    sink = RecordingSink()
    processor = SignalProcessor(router, forensic_sink=sink)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    symbol = SimpleNamespace(value="BTCUSDT")
    signal = SimpleNamespace(
        symbol=symbol, signal_type=SimpleNamespace(value="BUY"),
        confidence=SimpleNamespace(value=0.7), strength=0.8, timestamp=now,
    )
    observation = SimpleNamespace(
        symbol=symbol, observation_type="test", timestamp=now,
    )
    engine = SimpleNamespace(process_observation=lambda _observation: signal)
    processor._process_observation(
        SignalEvent(EventType.MARKET_OBSERVATION, observation, timestamp=now), engine,
    )
    assert len(sink.engine_calls) == 1
    assert len(router.interpreted) == 1

    fused = SimpleNamespace(
        symbol=symbol, dominant_bias=SimpleNamespace(value="BUY"),
        confidence=SimpleNamespace(value=0.7), regime_context="test",
        metadata={}, timestamp=now,
    )
    fusion = SimpleNamespace(fuse_signals=lambda _signals: fused)
    processor._process_interpreted_signal(
        SignalEvent(EventType.INTERPRETED_SIGNAL, signal, timestamp=now), fusion,
    )
    assert len(sink.fusion_calls) == 1
    assert len(router.fused) == 1


def test_default_forensic_sink_is_existing_live_singleton():
    from infrastructure.logging.forensic_logger import forensic_logger

    processor = SignalProcessor(RecordingRouter())
    assert processor._get_forensic_sink() is forensic_logger
