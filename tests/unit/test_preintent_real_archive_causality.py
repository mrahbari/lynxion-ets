"""Qualification-only tests for the frozen public candle capture.

These tests never calculate forward returns or study outcomes.
"""

import hashlib
import json
import socket
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from infrastructure.replay.closed_bar_decision_driver import ClosedBarDecisionDriver
from infrastructure.replay.decision_run_scope import ReplayDecisionRunScope
from infrastructure.replay.historical_closed_bar_source import HistoricalClosedBarSource
from infrastructure.replay.preintent_candle_capture import load_frozen_capture


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/research/pre_intent/candle_capture_v1/capture_manifest.json"
WARMUP_START = datetime(2026, 6, 1, tzinfo=timezone.utc)
EVALUATION_END = datetime(2026, 7, 1, tzinfo=timezone.utc)
CUTS = (
    datetime(2026, 6, 8, tzinfo=timezone.utc),
    datetime(2026, 6, 18, tzinfo=timezone.utc),
    datetime(2026, 6, 28, tzinfo=timezone.utc),
)


def _hash(trace):
    payload = json.dumps(trace, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _run(bars, through):
    scope = ReplayDecisionRunScope(WARMUP_START)
    try:
        source = HistoricalClosedBarSource(bars)
        settings = SimpleNamespace(watcher=SimpleNamespace(historical_candle_watcher_enabled=True))
        ClosedBarDecisionDriver(scope, source, settings).run_through(through)
        return tuple(scope.decision_trace)
    finally:
        scope.close()


def test_frozen_capture_quality_and_fixed_windows():
    bars, counts = load_frozen_capture(MANIFEST, ROOT)
    assert len(bars) == 1536
    assert counts["BTCUSDT"] == {
        "outside_leading": 24, "warmup": 50, "evaluation": 670,
        "outside_trailing": 24, "total": 768,
        "first_open_time": "2026-05-31T00:00:00+00:00",
        "last_availability_time": "2026-07-02T00:00:00+00:00",
    }
    assert counts["ETHUSDT"] == counts["BTCUSDT"]
    assert {bar.symbol for bar in bars} == {"BTCUSDT", "ETHUSDT"}
    assert all(bar.close_time <= EVALUATION_END for bar in bars
               if WARMUP_START <= bar.open_time < EVALUATION_END)


def test_real_archive_repeated_trace_and_three_prefix_cuts(monkeypatch):
    def deny_connect(*_args, **_kwargs):
        raise AssertionError("network capability reached during replay")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    bars, _ = load_frozen_capture(MANIFEST, ROOT)
    study_bars = tuple(bar for bar in bars
                       if WARMUP_START <= bar.open_time < EVALUATION_END)
    assert len(study_bars) == 1440

    full = _run(study_bars, EVALUATION_END)
    repeated = _run(study_bars, EVALUATION_END)
    assert _hash(full) == _hash(repeated)
    assert {row["event_type"] for row in full} >= {
        "market_observation", "interpreted_signal", "fused_signal"
    }

    for cut in CUTS:
        prefix_bars = tuple(bar for bar in study_bars if bar.close_time <= cut)
        prefix = _run(prefix_bars, cut)
        full_through_cut = tuple(row for row in full
                                 if datetime.fromisoformat(row["timestamp"]) <= cut)
        assert _hash(prefix) == _hash(full_through_cut), cut.isoformat()

    evaluation_fused = (row for row in full
                        if row["event_type"] == "fused_signal"
                        and datetime.fromisoformat(row["timestamp"]) >
                        datetime(2026, 6, 3, 2, tzinfo=timezone.utc))
    bias_counts = Counter(row["data"]["dominant_bias"] for row in evaluation_fused)
    # This is a pre-outcome eligibility count, not an economic finding.
    assert bias_counts == {"NEUTRAL": 1340}
