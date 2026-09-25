"""Closed-bar-only subset ingress into the canonical decision scope.

No unavailable live watcher is approximated. The existing historical-candle
watcher receives only bars validated complete by HistoricalClosedBarSource.
"""

from domain.value_objects import Symbol
from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter


class ClosedBarDecisionDriver:
    def __init__(self, scope, source, settings):
        self.scope = scope
        self.source = source
        self.settings = settings
        self.watchers = {}
        self._processed = set()

    def run_through(self, decision_time):
        reached = []
        for bar in self.source.completed_through(decision_time):
            key = (bar.symbol, bar.timeframe)
            identity = (key, bar.close_time)
            if identity in self._processed:
                continue
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
                # This value comes from the already-completed, validated source bar.
                observation.market_price = bar.close
                event_types = self.scope.process_observation(observation)
                reached.append((observation, event_types))
            self._processed.add(identity)
        return tuple(reached)
