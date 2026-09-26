"""Closed-bar-only subset ingress into the canonical decision scope.

No unavailable live watcher is approximated. The existing historical-candle
watcher receives only bars validated complete by HistoricalClosedBarSource.
"""

from domain.value_objects import Symbol
from itertools import groupby
from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter


class ClosedBarDecisionDriver:
    def __init__(self, scope, source, settings, strategy_history_feed=None):
        self.scope = scope
        self.source = source
        self.settings = settings
        self.strategy_history_feed = strategy_history_feed
        self.watchers = {}
        self._processed = set()

    def run_through(self, decision_time):
        reached = []
        bars = [bar for bar in self.source.completed_through(decision_time)
                if ((bar.symbol, bar.timeframe), bar.close_time) not in self._processed]
        for close_time, group in groupby(bars, key=lambda bar: bar.close_time):
            same_time_bars = tuple(group)
            # Every same-time HTF bar is closed before decisions at this time,
            # but later bars must never enter an earlier strategy buffer.
            if self.strategy_history_feed is not None:
                for bar in same_time_bars:
                    self.strategy_history_feed.accept(bar, close_time)
            for bar in same_time_bars:
                key = (bar.symbol, bar.timeframe)
                identity = (key, bar.close_time)
                watcher = self.watchers.get(key)
                if watcher is None:
                    watcher = HistoricalCandleWatcherAdapter(
                        self.settings, "HistoricalCandleWatcherAdapter", bar.symbol)
                    self.watchers[key] = watcher
                watcher.update_data({"candle": {
                    "open": bar.open, "high": bar.high, "low": bar.low,
                    "close": bar.close, "volume": bar.volume,
                    "close_time": bar.close_time,
                }})
                observation = watcher.analyze(Symbol(bar.symbol))
                if observation is not None:
                    if observation.timestamp != bar.close_time:
                        raise ValueError("historical watcher did not preserve completed-bar time")
                    # Live MonitoringAnalysisService attaches the watcher registry
                    # key before publishing. Preserve that same identity so Engine
                    # and Fusion select their existing live interpretation path.
                    if observation.metadata is None:
                        observation.metadata = {}
                    observation.metadata.setdefault("watcher_name", "historical_candle")
                    # This value comes from the already-completed, validated source bar.
                    observation.market_price = bar.close
                    event_types = self.scope.process_observation(observation)
                    reached.append((observation, event_types))
                self._processed.add(identity)
        return tuple(reached)
