"""Minimal application-time boundary for event-driven components."""

from datetime import datetime, timedelta


class LiveClock:
    def now(self):
        return datetime.now()


class ReplayClock:
    def __init__(self, initial_time):
        self._validate(initial_time)
        self._time = initial_time

    @staticmethod
    def _validate(value):
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("replay time must be timezone-aware UTC")

    def now(self):
        return self._time

    def advance(self, event_time):
        self._validate(event_time)
        if event_time < self._time:
            raise ValueError("replay clock cannot move backward")
        self._time = event_time
