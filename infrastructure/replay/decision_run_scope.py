"""Isolated canonical decision composition; no execution or broker capability.

This is an intermediate ApplicationRunScope slice. It deliberately accepts
causal MarketObservations, not historical rows or mock fused signals.
"""

from queue import Empty

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from infrastructure.aggregators.signal_aggregator import SignalAggregator
from infrastructure.engines.engine_service import EngineService
from infrastructure.fusion.fusion_service import FusionService
from infrastructure.fusion.hierarchical.hierarchical_fusion_service import HierarchicalFusionService
from infrastructure.messaging.clock import ReplayClock
from infrastructure.messaging.event_system import EventRouter, SignalProcessor
from infrastructure.orchestrators.architecture_orchestrator import ArchitectureOrchestrator
from infrastructure.strategies.strategy_manager import StrategyManager
from infrastructure.replay.normalized_decision_trace import normalize_event


class _RunTraceSink:
    """Run-local observability sink; never opens production files."""

    def __init__(self):
        self.records = []

    def __getattr__(self, method):
        if not method.startswith("log_"):
            raise AttributeError(method)

        def record(*args, **kwargs):
            self.records.append((method, args, kwargs))

        return record


class _RunTradeTracker:
    def __init__(self):
        self.events = []

    def register_trade(self, **kwargs):
        self.events.append(("enter", kwargs))

    def close_trade(self, **kwargs):
        self.events.append(("exit", kwargs))


class ReplayDecisionRunScope:
    """Owns fresh decision state; order/risk enforcement is not composed yet."""

    def __init__(self, initial_time):
        self.clock = ReplayClock(initial_time)
        self.router = EventRouter()
        self.trace_sink = _RunTraceSink()
        self.decision_trace = []
        self.trade_tracker = _RunTradeTracker()
        self.risk_manager = EnterpriseRiskManager(
            clock=self.clock, trade_tracker_instance=self.trade_tracker,
            start_correlation_worker=False)
        self.engine = EngineService()
        self.hierarchical_fusion = HierarchicalFusionService(
            clock=self.clock, logger=self.trace_sink)
        self.fusion = FusionService(
            hierarchical_service=self.hierarchical_fusion, clock=self.clock)
        self.strategies = StrategyManager()
        for adapter in self.strategies.strategies.values():
            # No point-in-time archive is bound yet. An empty result is safer
            # than the adapter's live global/download-capable fallback.
            adapter.bind_history_loader(lambda symbol, config: [])
        self.aggregator = SignalAggregator(
            clock=self.clock, router=self.router, strategy_selector=self.strategies,
            synchronous=True)
        self.processor = SignalProcessor(
            self.router, forensic_sink=self.trace_sink,
            price_recorder=self.risk_manager, clock=self.clock)
        self.architecture = ArchitectureOrchestrator(
            engine_service=self.engine, fusion_service=self.fusion,
            strategy_manager=self.strategies, event_router=self.router,
            signal_processor_instance=self.processor,
            signal_aggregator_instance=self.aggregator,
            owns_live_globals=False)
        self.architecture.start()

    def process_observation(self, observation):
        """Synchronously drain the same router handlers used by Live."""
        self.clock.advance(observation.timestamp)
        self.router.publish_observation(observation, source="HistoricalDataSource")
        reached = []
        while True:
            try:
                event = self.router.event_queue.get_nowait()
            except Empty:
                break
            reached.append(event.event_type)
            self.decision_trace.append(normalize_event(event))
            self.router._route_event(event)
        return tuple(reached)

    def close(self):
        self.architecture.stop()
        # Synchronous mode owns no aggregation thread. Do not flush queued
        # candidates during disposal; decisions occur only at event boundaries.
        self.aggregator.is_running = False
