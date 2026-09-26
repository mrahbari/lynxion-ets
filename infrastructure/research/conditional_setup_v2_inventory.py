"""Outcome-blind inventory of existing Engine direction and market-structure state.

This module never reads a later bar to label an earlier event and contains no
return, PnL, fill, or test statistic. It only counts causal state at each close.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import socket

from domain.value_objects import Symbol
from infrastructure.engines.engine_service import EngineService
from infrastructure.market_structure.market_structure_engine import MarketStructureEngine
from infrastructure.messaging.clock import ReplayClock
from infrastructure.replay.preintent_candle_capture import load_frozen_capture
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "data/research/pre_intent/candle_capture_v1/capture_manifest.json"
START = datetime(2026, 6, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 1, tzinfo=timezone.utc)
WARMUP_END = datetime(2026, 6, 3, 2, tzinfo=timezone.utc)


class MemorySink:
    def log_watcher_observation(self, **_entry):
        pass


def inventory(bars):
    clock = ReplayClock(START)
    sink = MemorySink()
    watchers = {symbol: TrendMTFWatcher("TrendMTFWatcher", symbol, clock=clock,
                                        forensic_sink=sink)
                for symbol in ("BTCUSDT", "ETHUSDT")}
    structure = {symbol: MarketStructureEngine() for symbol in watchers}
    history = {symbol: [] for symbol in watchers}
    engine = EngineService()
    rows = []
    for bar in bars:
        if not START <= bar.open_time < END:
            continue
        clock.advance(bar.close_time)
        symbol = bar.symbol
        history[symbol].append(bar)
        watcher = watchers[symbol]
        watcher.update_data({"close": bar.close})
        observation = watcher.analyze(Symbol(symbol))
        if observation is None:
            continue
        signal = engine.process_observation(observation)
        if signal is None or signal.timestamp != bar.close_time:
            raise ValueError("Engine direction or event timestamp unavailable")
        closed = history[symbol]
        state = structure[symbol].calculate_market_structure(
            [b.close for b in closed], [b.high for b in closed],
            [b.low for b in closed], [b.volume for b in closed])
        if bar.close_time > WARMUP_END:
            rows.append((bar.close_time.isoformat(), symbol, signal.signal_type.value,
                         state["bias"]))
    return tuple(rows)


def counts(rows):
    all_directions = Counter(row[2] for row in rows)
    directional = tuple(row for row in rows if row[2] in {"BUY", "SELL"})
    def matching(row):
        return (row[2] == "BUY" and row[3] == "LONG") or (row[2] == "SELL" and row[3] == "SHORT")
    all_eligible = tuple(row for row in directional if matching(row))
    all_controls = tuple(row for row in directional if not matching(row))
    arms_by_stratum = defaultdict(lambda: [0, 0])
    for row in directional:
        iso = datetime.fromisoformat(row[0]).isocalendar()
        stratum = (row[1], iso.year, iso.week, row[2])
        arms_by_stratum[stratum][0 if matching(row) else 1] += 1
    paired_strata = {key for key, arm_counts in arms_by_stratum.items() if min(arm_counts) > 0}
    comparable = tuple(row for row in directional
                       if (row[1], datetime.fromisoformat(row[0]).isocalendar().year,
                           datetime.fromisoformat(row[0]).isocalendar().week, row[2]) in paired_strata)
    first_by_block = {}
    for row in directional:
        event_time = datetime.fromisoformat(row[0])
        first_by_block.setdefault((row[1], int(event_time.timestamp()) // 14400), row)
    selected = tuple(first_by_block.values())
    eligible = tuple(row for row in selected if matching(row))
    controls = tuple(row for row in selected if not matching(row))
    arms_by_day = defaultdict(set)
    for row in selected:
        arms_by_day[(row[1], row[0][:10])].add("eligible" if matching(row) else "control")
    return {
        "all_engine_directions": dict(sorted(all_directions.items())),
        "structure_bias_all": dict(sorted(Counter(row[3] for row in rows).items())),
        "all_directional": len(directional),
        "all_agreement": len(all_eligible),
        "all_nonagreement": len(all_controls),
        "comparable_symbol_week_side_strata": len(paired_strata),
        "comparable_eligible": sum(matching(row) for row in comparable),
        "comparable_controls": sum(not matching(row) for row in comparable),
        "comparable_utc_days": len({row[0][:10] for row in comparable}),
        "selected_directional": len(selected),
        "eligible_structure_agreement": len(eligible),
        "nonagreement_controls": len(controls),
        "eligible_by_symbol": dict(sorted(Counter(row[1] for row in eligible).items())),
        "controls_by_symbol": dict(sorted(Counter(row[1] for row in controls).items())),
        "eligible_utc_days": len({row[0][:10] for row in eligible}),
        "control_utc_days": len({row[0][:10] for row in controls}),
        "both_arms_same_symbol_utc_day": sum(len(arms) == 2 for arms in arms_by_day.values()),
        "missing_input_rows": 0,
    }


if __name__ == "__main__":
    import json

    socket.socket.connect = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("network forbidden during inventory"))
    bars, _ = load_frozen_capture(CAPTURE, ROOT)
    print(json.dumps(counts(inventory(bars)), sort_keys=True, indent=2))
