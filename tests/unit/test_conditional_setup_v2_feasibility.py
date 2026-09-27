"""Frozen V2 sample gate, with no future-price labels or network."""

import hashlib
import json
import socket
from datetime import datetime, timezone

from infrastructure.replay.conditional_setup_v2_capture import qualify_capture
from infrastructure.research.conditional_setup_v2_feasibility import sample_floor, trace


def _sha(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def test_v2_preoutcome_sample_floor_and_causal_trace(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("network forbidden")))
    bars, _ = qualify_capture()
    full = trace(bars)
    assert trace(bars) == full
    assert len(full) == 4032
    for cut in (datetime(2026, 7, 20, tzinfo=timezone.utc),
                datetime(2026, 8, 20, tzinfo=timezone.utc),
                datetime(2026, 9, 15, tzinfo=timezone.utc)):
        prefix_bars = tuple(bar for bar in bars if bar.close_time <= cut)
        assert trace(prefix_bars) == tuple(row for row in full if datetime.fromisoformat(row[0]) <= cut)
    btc_only = trace(tuple(bar for bar in bars if bar.symbol == "BTCUSDT"))
    assert btc_only == tuple(row for row in full if row[1] == "BTCUSDT")
    result = sample_floor(full)
    assert result["status"] == "V2_DATA_LIMITED"
    assert result["eligible"]["n"] == 556
    assert result["control"]["n"] == 196
    assert result["paired_strata"] == 40
    assert result["paired_iso_weeks"] == 12
    assert result["censored_at_boundary"] == 0
    assert _sha(full) == "092bae2e6df268e203925151b8c03b29c7ff67f1fdd6fade635760998a4c45fd"
