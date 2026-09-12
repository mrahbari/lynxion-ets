#!/usr/bin/env python3
"""Frozen deterministic statistical primitives for the C-35 aggregate evaluator."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


BOOTSTRAP_SEED = 350035
BOOTSTRAP_SAMPLES = 10_000


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires observations")
    return sum(values) / len(values)


def profit_factor(values: list[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    if losses == 0:
        return None if gains == 0 else math.inf
    return gains / losses


def max_drawdown(values: list[float]) -> float:
    equity = peak = 1.0
    drawdown = 0.0
    for value in values:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = max(drawdown, (peak - equity) / peak)
    return drawdown


def _utc_day(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).date().isoformat()


def _linear_percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    rank = (len(ordered) - 1) * quantile
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def daily_clustered_lower_bound(
    outcomes: list[dict[str, Any]],
    *,
    field: str = "net_return_primary_0_30pct",
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> float:
    if not outcomes or samples <= 0:
        raise ValueError("bootstrap requires outcomes and positive sample count")
    clusters: dict[str, list[float]] = defaultdict(list)
    for row in outcomes:
        clusters[_utc_day(int(row["exit_open_time"]))].append(float(row[field]))
    days = sorted(clusters)
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        draw = [rng.choice(days) for _ in days]
        values = [value for day in draw for value in clusters[day]]
        estimates.append(mean(values))
    return _linear_percentile(estimates, 0.025)


def chronological_week_folds(outcomes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not outcomes:
        raise ValueError("folds require outcomes")
    def week(epoch: int) -> tuple[int, int]:
        iso = datetime.fromtimestamp(epoch, timezone.utc).isocalendar()
        return iso.year, iso.week
    weeks = sorted({
        value
        for row in outcomes
        for value in (week(int(row["entry_open_time"])), week(int(row["exit_open_time"])))
    })
    rank = {value: index for index, value in enumerate(weeks)}
    folds = [[] for _ in range(4)]
    for row in sorted(outcomes, key=lambda item: (int(item["exit_open_time"]), item["signal_key"])):
        entry_week = week(int(row["entry_open_time"]))
        exit_week = week(int(row["exit_open_time"]))
        entry_fold = min(3, 4 * rank[entry_week] // len(weeks))
        exit_fold = min(3, 4 * rank[exit_week] // len(weeks))
        if entry_fold != exit_fold:
            raise ValueError("position crosses a chronological fold boundary")
        folds[exit_fold].append(row)
    return folds
