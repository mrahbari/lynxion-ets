#!/usr/bin/env python3
"""Pure point-in-time signal evaluator for preregistered C-35."""

from __future__ import annotations

import math
import statistics
from typing import Any


INTERVAL_SECONDS = 900
BOUNDARY_EPOCH = 1789087244
UNIVERSE = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT")


def _f(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def _percentile_linear(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    rank = (len(ordered) - 1) * fraction
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _candidate(symbol: str, candles: list[dict[str, Any]], decision_time: int, boundary: int):
    if symbol not in UNIVERSE or decision_time % 3600 or len(candles) < 2898:
        return None
    rows = sorted(candles, key=lambda row: int(row.get("open_time", -1)))
    rows = [row for row in rows if int(row.get("open_time", -1)) <= decision_time - INTERVAL_SECONDS]
    if len(rows) < 2898:
        return None
    rows = rows[-2898:]
    expected_start = decision_time - INTERVAL_SECONDS * len(rows)
    if any(int(row.get("open_time", -1)) != expected_start + index * INTERVAL_SECONDS
           for index, row in enumerate(rows)):
        return None
    decision = rows[-1]
    decision_open = int(decision["open_time"])
    if decision_open <= boundary:
        return None

    ntr: list[float] = []
    for previous, current in zip(rows, rows[1:]):
        high, low, close = _f(current.get("high")), _f(current.get("low")), _f(current.get("close"))
        previous_close = _f(previous.get("close"))
        if not all(math.isfinite(value) and value > 0 for value in (high, low, close, previous_close)):
            return None
        true_range = max(high - low, abs(high - previous_close), abs(low - previous_close))
        ntr.append(true_range / close)

    historical = ntr[-2897:-17]
    compressed = ntr[-17:-1]
    if len(historical) != 2880 or len(compressed) != 16:
        return None
    compression_threshold = _percentile_linear(historical, 0.20)
    compression_value = statistics.median(compressed)
    if not compression_value < compression_threshold:
        return None

    prior = rows[-17:-1]
    decision_high = _f(decision.get("high"))
    decision_low = _f(decision.get("low"))
    decision_close = _f(decision.get("close"))
    decision_volume = _f(decision.get("volume"))
    prior_volumes = [_f(row.get("volume")) for row in rows[-97:-1]]
    if not all(math.isfinite(value) and value >= 0 for value in prior_volumes + [decision_volume]):
        return None
    decision_ntr = ntr[-1]
    if decision_ntr < 0.0045 or decision_volume < 1.5 * statistics.median(prior_volumes):
        return None
    if decision_close > max(_f(row.get("high")) for row in prior):
        side = "LONG"
    elif decision_close < min(_f(row.get("low")) for row in prior):
        side = "SHORT"
    else:
        return None
    return {
        "candidate": "C-35",
        "symbol": symbol,
        "side": side,
        "decision_time": decision_time,
        "decision_bar_open": decision_open,
        "entry_open_time": decision_time,
        "exit_open_time": decision_time + 8 * INTERVAL_SECONDS,
        "decision_normalized_true_range": decision_ntr,
        "compression_median": compression_value,
        "compression_threshold": compression_threshold,
    }


def evaluate_decision(
    candles_by_symbol: dict[str, list[dict[str, Any]]],
    decision_time: int,
    *,
    boundary: int = BOUNDARY_EPOCH,
) -> dict[str, Any] | None:
    candidates = [
        candidate for symbol in UNIVERSE
        if (candidate := _candidate(symbol, candles_by_symbol.get(symbol, []), decision_time, boundary))
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: (-row["decision_normalized_true_range"], row["symbol"]))[0]
