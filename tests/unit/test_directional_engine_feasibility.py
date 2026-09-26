"""Outcome-blind feasibility of existing rolling-trend watcher -> Engine semantics."""

import hashlib
import json
import socket
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from domain.value_objects import Symbol
from infrastructure.engines.engine_service import EngineService
from infrastructure.messaging.clock import ReplayClock
from infrastructure.messaging.clock import LiveClock
from infrastructure.replay.preintent_candle_capture import load_frozen_capture
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
from infrastructure.logging.forensic_logger import forensic_logger


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/research/pre_intent/candle_capture_v1/capture_manifest.json"
START = datetime(2026, 6, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 1, tzinfo=timezone.utc)
WARMUP_END = datetime(2026, 6, 3, 2, tzinfo=timezone.utc)
CUTS = (datetime(2026, 6, day, tzinfo=timezone.utc) for day in (8, 18, 28))


class MemoryForensicSink:
    def __init__(self):
        self.entries = []

    def log_watcher_observation(self, **entry):
        self.entries.append(entry)


def _trace(bars, through):
    clock = ReplayClock(START)
    sink = MemoryForensicSink()
    watchers = {symbol: TrendMTFWatcher("TrendMTFWatcher", symbol, clock=clock,
                                        forensic_sink=sink)
                for symbol in ("BTCUSDT", "ETHUSDT")}
    engine = EngineService()
    rows = []
    for bar in bars:
        if bar.close_time > through:
            break
        clock.advance(bar.close_time)
        watcher = watchers[bar.symbol]
        watcher.update_data({"close": bar.close})
        observation = watcher.analyze(Symbol(bar.symbol))
        if observation is None:
            continue
        assert observation.timestamp == bar.close_time
        assert observation.metadata["price_history_length"] <= 90
        interpreted = engine.process_observation(observation)
        assert interpreted is not None
        assert interpreted.timestamp == bar.close_time
        rows.append((bar.close_time.isoformat(), bar.symbol, observation.observation_type,
                     interpreted.signal_type.value))
    return tuple(rows), sink


def _digest(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def test_trend_live_defaults_and_explicit_run_dependencies():
    live = TrendMTFWatcher("TrendMTFWatcher", "BTCUSDT")
    assert isinstance(live.clock, LiveClock)
    assert live.forensic_sink is forensic_logger
    clock = ReplayClock(START)
    sink = MemoryForensicSink()
    isolated = TrendMTFWatcher("TrendMTFWatcher", "BTCUSDT", clock=clock,
                               forensic_sink=sink)
    assert isolated.clock is clock and isolated.forensic_sink is sink
    assert isolated.price_history is not live.price_history


def test_existing_trend_engine_direction_is_causal_and_reproducible(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *_args, **_kwargs:
                        (_ for _ in ()).throw(AssertionError("network access forbidden")))
    bars, _ = load_frozen_capture(MANIFEST, ROOT)
    study_bars = tuple(bar for bar in bars if START <= bar.open_time < END)
    assert len(study_bars) == 1440
    full, sink = _trace(study_bars, END)
    repeated, second_sink = _trace(study_bars, END)
    assert _digest(full) == _digest(repeated)
    assert len(sink.entries) == len(second_sink.entries) == len(full)
    for cut in CUTS:
        prefix, _ = _trace(tuple(bar for bar in study_bars if bar.close_time <= cut), cut)
        assert _digest(prefix) == _digest(tuple(row for row in full
                                                if datetime.fromisoformat(row[0]) <= cut))
    evaluation = tuple(row for row in full if datetime.fromisoformat(row[0]) > WARMUP_END)
    assert len(evaluation) == 1340
    counts = Counter(row[3] for row in evaluation)
    print("outcome-blind Engine direction counts:", dict(sorted(counts.items())))
    assert set(counts) <= {"BUY", "SELL", "NEUTRAL"}
    directional = tuple(row for row in evaluation if row[3] in {"BUY", "SELL"})
    first_per_symbol_block = {}
    for row in directional:
        event_time = datetime.fromisoformat(row[0])
        block = (row[1], int(event_time.timestamp()) // (4 * 3600))
        first_per_symbol_block.setdefault(block, row)
    selected = tuple(first_per_symbol_block.values())
    selected_counts = Counter(row[1] for row in selected)
    selected_days = {symbol: len({row[0][:10] for row in selected if row[1] == symbol})
                     for symbol in ("BTCUSDT", "ETHUSDT")}
    print("outcome-blind full/selected trace SHA-256:", _digest(full), _digest(selected))
    assert _digest(full) == "e6efa4b9625812dbb864187b6ee87b5e87b939cc1729f040e092fe9b12c25126"
    assert _digest(selected) == "d5f836229267d36d0f9ec62fa10281877618daf3d0ea939d40f2627688fdb54f"
    print("outcome-blind non-overlap counts:", dict(sorted(selected_counts.items())))
    print("outcome-blind distinct UTC days:", selected_days)
    assert len(selected) >= 100
    assert all(days >= 20 for days in selected_days.values())
