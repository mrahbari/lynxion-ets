"""Event-time driver for the existing Risk correlation calculation.

One call represents one complete timestamp batch: all causal prices at that
timestamp precede a due same-time publication, which precedes Risk sizing.
"""

from datetime import timedelta


class ReplayCorrelationScheduler:
    def __init__(self, risk_manager, clock):
        if risk_manager.worker_thread is not None:
            raise ValueError("replay correlation scheduler requires a worker-free Risk manager")
        self._risk_manager = risk_manager
        self._clock = clock
        self._interval = timedelta(seconds=risk_manager.correlation_update_interval_sec)
        if self._interval <= timedelta(0):
            raise ValueError("correlation interval must be positive")
        self._next_update = clock.now() + self._interval
        self._last_event_time = None
        self.publications = []

    def _publish(self, boundary):
        before = self._risk_manager.get_correlation_snapshot().version
        self._risk_manager.recalculate_correlations()
        after = self._risk_manager.get_correlation_snapshot().version
        if after != before:
            self.publications.append((boundary, after))
        self._next_update = boundary + self._interval

    def advance(self, event_time, price_updates=()):
        """Process one complete event-time batch before any same-time sizing."""
        if self._last_event_time is not None and event_time <= self._last_event_time:
            raise ValueError("event-time batches must be strictly increasing")
        # Earlier boundaries cannot see prices arriving at event_time.
        while self._next_update < event_time:
            self._clock.advance(self._next_update)
            self._publish(self._next_update)
        self._clock.advance(event_time)
        for symbol, price in price_updates:
            self._risk_manager.record_price(symbol, price)
        # At a tie, the causal price batch precedes publication, then sizing.
        if self._next_update == event_time:
            self._publish(self._next_update)
        self._last_event_time = event_time
        return self._risk_manager.get_correlation_snapshot()
