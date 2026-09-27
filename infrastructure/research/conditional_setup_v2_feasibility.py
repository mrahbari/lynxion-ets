"""V2 pre-outcome direction/setup trace and frozen sample floor only.

No next-bar price, future return, or economic outcome is read here.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from domain.value_objects import Symbol
from infrastructure.engines.engine_service import EngineService
from infrastructure.market_structure.market_structure_engine import MarketStructureEngine
from infrastructure.messaging.clock import ReplayClock
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher


START = datetime(2026, 7, 1, tzinfo=timezone.utc)
EVALUATION_START = datetime(2026, 7, 4, tzinfo=timezone.utc)
END = datetime(2026, 9, 26, tzinfo=timezone.utc)
SYMBOLS = ("BTCUSDT", "ETHUSDT")


class MemorySink:
    def log_watcher_observation(self, **_entry):
        pass


def trace(bars):
    """Produce only current-bar decision and structure state, with fresh scope."""
    clock = ReplayClock(START)
    watchers = {symbol: TrendMTFWatcher("TrendMTFWatcher", symbol, clock=clock,
                                        forensic_sink=MemorySink()) for symbol in SYMBOLS}
    structure = {symbol: MarketStructureEngine() for symbol in SYMBOLS}
    history = {symbol: [] for symbol in SYMBOLS}
    engine = EngineService()
    output = []
    for bar in bars:
        if not START <= bar.open_time < END:
            raise ValueError("bar outside frozen V2 acquisition interval")
        clock.advance(bar.close_time)
        history[bar.symbol].append(bar)
        watcher = watchers[bar.symbol]
        watcher.update_data({"close": bar.close})
        observation = watcher.analyze(Symbol(bar.symbol))
        if observation is None:
            continue
        if observation.timestamp != bar.close_time:
            raise ValueError("Watcher event-time mismatch")
        signal = engine.process_observation(observation)
        if signal is None or signal.timestamp != bar.close_time:
            raise ValueError("Engine event-time mismatch")
        closed = history[bar.symbol]
        state = structure[bar.symbol].calculate_market_structure(
            [item.close for item in closed], [item.high for item in closed],
            [item.low for item in closed], [item.volume for item in closed])
        if bar.open_time >= EVALUATION_START:
            if signal.signal_type.value not in {"BUY", "SELL", "NEUTRAL"}:
                raise ValueError("unknown Engine direction")
            if state["bias"] not in {"LONG", "SHORT", "NEUTRAL"}:
                raise ValueError("unknown structural bias")
            output.append((bar.close_time.isoformat(), bar.symbol,
                           signal.signal_type.value, state["bias"]))
    return tuple(output)


def _arm(row):
    side, bias = row[2], row[3]
    return "eligible" if ((side == "BUY" and bias == "LONG") or
                          (side == "SELL" and bias == "SHORT")) else "control"


def sample_floor(rows):
    """Apply all preregistered count/date/side/week floors before labels."""
    if len(rows) != 4032:
        raise ValueError("incomplete frozen V2 evaluation trace")
    direction_counts = Counter(row[2] for row in rows)
    directional = tuple(row for row in rows if row[2] in {"BUY", "SELL"})
    # The last acquisition bar lacks a next completed bar inside the fixed window.
    censor_boundary = END - timedelta(hours=1)
    uncensored = tuple(row for row in directional
                       if datetime.fromisoformat(row[0]) <= censor_boundary)
    censored = len(directional) - len(uncensored)
    by_stratum = defaultdict(lambda: Counter())
    for row in uncensored:
        time = datetime.fromisoformat(row[0])
        week = time.isocalendar()
        by_stratum[(row[1], week.year, week.week, row[2])][_arm(row)] += 1
    paired = {key for key, arms in by_stratum.items() if arms["eligible"] and arms["control"]}
    comparable = tuple(row for row in uncensored
                       if (row[1], datetime.fromisoformat(row[0]).isocalendar().year,
                           datetime.fromisoformat(row[0]).isocalendar().week, row[2]) in paired)
    arms = {arm: tuple(row for row in comparable if _arm(row) == arm)
            for arm in ("eligible", "control")}
    details = {}
    for arm, events in arms.items():
        details[arm] = {"n": len(events),
                        "utc_days": len({row[0][:10] for row in events}),
                        "by_symbol": dict(sorted(Counter(row[1] for row in events).items())),
                        "by_side": dict(sorted(Counter(row[2] for row in events).items()))}
    paired_weeks = len({(year, week) for _, year, week, _ in paired})
    passed = (all(details[arm]["n"] >= 300 and details[arm]["utc_days"] >= 40
                  and all(details[arm]["by_symbol"].get(symbol, 0) >= 20 for symbol in SYMBOLS)
                  and all(details[arm]["by_side"].get(side, 0) >= 50 for side in ("BUY", "SELL"))
                  for arm in arms) and paired_weeks >= 8)
    return {"status": "SAMPLE_FEASIBILITY_PASS" if passed else "V2_DATA_LIMITED",
            "evaluation_outputs": len(rows), "direction_counts": dict(sorted(direction_counts.items())),
            "directional_total": len(directional), "censored_at_boundary": censored,
            "paired_strata": len(paired), "paired_iso_weeks": paired_weeks,
            "eligible": details["eligible"], "control": details["control"]}
