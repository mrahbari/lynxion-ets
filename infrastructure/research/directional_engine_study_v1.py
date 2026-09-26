"""Frozen V1 predictive labels for existing Lynxion watcher -> Engine output.

Run only after the preregistration is committed. Never sends network requests,
constructs execution intents, simulates fills, or writes research outcomes.
"""

import hashlib
import json
import random
import socket
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from domain.value_objects import Symbol
from infrastructure.engines.engine_service import EngineService
from infrastructure.messaging.clock import ReplayClock
from infrastructure.replay.preintent_candle_capture import load_frozen_capture
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/path_integrity/canonical_replay/DIRECTIONAL_EDGE_STUDY_V1_PREREGISTRATION.md"
PROTOCOL_SHA256 = "28e2224f640fb7c61765cedbc9a7d784b75d4ffee8eb9022a50173860147b206"
MANIFEST = ROOT / "data/research/pre_intent/candle_capture_v1/capture_manifest.json"
MANIFEST_SHA256 = "4832beedbbddb4ea55da8882994cb7497f77298003f09e9642046331e8533ffb"
FULL_TRACE_SHA256 = "e6efa4b9625812dbb864187b6ee87b5e87b939cc1729f040e092fe9b12c25126"
SELECTED_TRACE_SHA256 = "d5f836229267d36d0f9ec62fa10281877618daf3d0ea939d40f2627688fdb54f"
START = datetime(2026, 6, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 1, tzinfo=timezone.utc)
WARMUP_END = datetime(2026, 6, 3, 2, tzinfo=timezone.utc)


def _digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


class MemoryForensicSink:
    def log_watcher_observation(self, **_entry):
        pass


def _decision_trace(bars):
    clock = ReplayClock(START)
    sink = MemoryForensicSink()
    watchers = {symbol: TrendMTFWatcher("TrendMTFWatcher", symbol, clock=clock,
                                        forensic_sink=sink)
                for symbol in ("BTCUSDT", "ETHUSDT")}
    engine = EngineService()
    rows = []
    for bar in bars:
        clock.advance(bar.close_time)
        watcher = watchers[bar.symbol]
        watcher.update_data({"close": bar.close})
        observation = watcher.analyze(Symbol(bar.symbol))
        if observation is None:
            continue
        if observation.timestamp != bar.close_time:
            raise ValueError("watcher event time is not causal bar close")
        signal = engine.process_observation(observation)
        if signal is None or signal.timestamp != bar.close_time:
            raise ValueError("Engine failed or changed event time")
        rows.append((bar.close_time.isoformat(), bar.symbol,
                     observation.observation_type, signal.signal_type.value))
    return tuple(rows)


def _mean_interval(events):
    by_day = defaultdict(list)
    for event in events:
        by_day[event["time"][:10]].append(event["primary_return"])
    days = tuple(sorted(by_day))
    rng = random.Random(20260926)
    boot = []
    for _ in range(10000):
        drawn = [rng.choice(days) for _ in days]
        values = [value for day in drawn for value in by_day[day]]
        boot.append(statistics.mean(values))
    boot.sort()
    return (boot[249], boot[9749])


def run():
    def deny_connect(*_args, **_kwargs):
        raise AssertionError("network capability forbidden")

    socket.socket.connect = deny_connect
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("frozen preregistration changed")
    if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise ValueError("frozen capture manifest changed")
    all_bars, _ = load_frozen_capture(MANIFEST, ROOT)
    bars = tuple(bar for bar in all_bars if START <= bar.open_time < END)
    if len(bars) != 1440:
        raise ValueError("frozen run coverage changed")
    full = _decision_trace(bars)
    if _digest(full) != FULL_TRACE_SHA256:
        raise ValueError("decision trace differs from pre-outcome freeze")
    evaluation = (row for row in full if datetime.fromisoformat(row[0]) > WARMUP_END)
    counts = Counter()
    first_by_block = {}
    for row in evaluation:
        counts[row[3]] += 1
        if row[3] not in {"BUY", "SELL"}:
            continue
        time = datetime.fromisoformat(row[0])
        block = (row[1], int(time.timestamp()) // 14400)
        first_by_block.setdefault(block, row)
    selected = tuple(first_by_block.values())
    if _digest(selected) != SELECTED_TRACE_SHA256:
        raise ValueError("selected event trace differs from pre-outcome freeze")
    if counts != {"BUY": 139, "SELL": 278, "NEUTRAL": 923} or len(selected) != 163:
        raise ValueError("outcome-blind feasibility changed")

    closes = {(bar.symbol, bar.close_time): bar.close for bar in bars}
    eligible, censored = [], []
    for row in selected:
        time = datetime.fromisoformat(row[0])
        symbol, side = row[1], row[3]
        first, fourth = closes.get((symbol, time + timedelta(hours=1))), closes.get((symbol, time + timedelta(hours=4)))
        if first is None or fourth is None:
            censored.append((row[0], symbol, side))
            continue
        base = closes[(symbol, time)]
        direction = 1 if side == "BUY" else -1
        eligible.append({"time": row[0], "symbol": symbol, "side": side,
                         "primary_return": direction * (fourth - base) / base,
                         "secondary_return": direction * (first - base) / base})
    if len(eligible) < 100 or any(len({e["time"][:10] for e in eligible if e["symbol"] == symbol}) < 20
                                  for symbol in ("BTCUSDT", "ETHUSDT")):
        return {"status": "INCONCLUSIVE_UNDERPOWERED", "eligible_n": len(eligible), "censored": censored}

    primary = [e["primary_return"] for e in eligible]
    interval = _mean_interval(eligible)
    week = lambda e: datetime.fromisoformat(e["time"]).isocalendar()[:2]
    week_values = defaultdict(list)
    for event in eligible:
        week_values[week(event)].append(event["primary_return"])
    by_week = {f"{year}-W{number:02d}": {"n": len(values), "mean": statistics.mean(values)}
               for (year, number), values in sorted(week_values.items())}
    leave_one_week_out = {f"{year}-W{number:02d}": statistics.mean(
        e["primary_return"] for e in eligible if week(e) != (year, number))
        for year, number in sorted(week_values)}
    by_symbol = {symbol: {"n": len(values), "mean": statistics.mean(values)}
                 for symbol in ("BTCUSDT", "ETHUSDT")
                 for values in [[e["primary_return"] for e in eligible if e["symbol"] == symbol]]}
    return {"status": "PREDICTIVE_SUPPORT" if interval[0] > 0 else "PREDICTIVE_NOT_SUPPORTED",
            "economic_edge": "NOT_TESTED_NO_EXECUTABLE_FILL_OR_COST_MODEL",
            "preregistration_sha256": PROTOCOL_SHA256,
            "decision_trace_sha256": FULL_TRACE_SHA256,
            "selected_trace_sha256": SELECTED_TRACE_SHA256,
            "evaluation_counts": dict(sorted(counts.items())),
            "selected_n": len(selected), "eligible_n": len(eligible), "censored": censored,
            "primary_mean": statistics.mean(primary), "primary_median": statistics.median(primary),
            "primary_stdev": statistics.stdev(primary), "primary_bootstrap_95_percentile": interval,
            "secondary_1h_mean": statistics.mean(e["secondary_return"] for e in eligible),
            "by_symbol": by_symbol, "by_week": by_week,
            "leave_one_week_out_mean": leave_one_week_out,
            "eligible_event_outcomes_sha256": _digest(eligible)}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))
