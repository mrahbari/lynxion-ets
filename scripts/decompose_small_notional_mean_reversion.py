#!/usr/bin/env python3
"""Execute TASK-0239's frozen small-notional/MeanReversion decomposition."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.performance_attribution import (
        _cost_adjusted_pnl,
        _final_records,
        _is_technical_demo,
        _number,
    )
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from performance_attribution import _cost_adjusted_pnl, _final_records, _is_technical_demo, _number


def _normalized_return(row: dict[str, str]) -> float | None:
    notional = _number(row, "entry_price") * _number(row, "quantity")
    return _cost_adjusted_pnl(row) / notional if notional > 0 else None


def _metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    pnl = [_cost_adjusted_pnl(row) for row in rows]
    returns = [value for row in rows if (value := _normalized_return(row)) is not None]
    wins = [value for value in pnl if value > 0]
    losses = [value for value in pnl if value < 0]
    gross_loss = abs(sum(losses))
    notional = sum(_number(row, "entry_price") * _number(row, "quantity") for row in rows)
    return {
        "n": len(rows),
        "cost_adjusted_pnl_usdt": round(sum(pnl), 8),
        "expectancy_usdt": round(sum(pnl) / len(rows), 8) if rows else None,
        "profit_factor": round(sum(wins) / gross_loss, 8) if gross_loss else None,
        "win_rate": round(len(wins) / len(rows), 8) if rows else None,
        "median_normalized_return": round(statistics.median(returns), 10) if returns else None,
        "mean_normalized_return": round(sum(returns) / len(returns), 10) if returns else None,
        "fee_to_notional": round(sum(_number(row, "fees_usdt") for row in rows) / notional, 10)
        if notional else None,
        "invalid_notional": len(rows) - len(returns),
    }


def _bootstrap_ci(values: list[float], *, seed: int, samples: int) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(samples))
    lower = means[int(0.025 * samples)]
    upper = means[min(samples - 1, int(0.975 * samples))]
    return [round(lower, 10), round(upper, 10)]


def _small(row: dict[str, str]) -> bool:
    return _number(row, "entry_price") * _number(row, "quantity") <= 25


def _mean_reversion(row: dict[str, str]) -> bool:
    return (row.get("strategy") or "").strip().lower() == "meanreversion"


def _week(row: dict[str, str]) -> str:
    value = (row.get("entry_timestamp") or "").replace("Z", "+00:00")
    year, week, _ = datetime.fromisoformat(value).isocalendar()
    return f"{year}-W{week:02d}"


def _band_comparison(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "small": _metrics([row for row in rows if _small(row)]),
        "larger": _metrics([row for row in rows if not _small(row)]),
    }


def _concentration(rows: list[dict[str, str]]) -> dict[str, Any]:
    pnl_by_symbol: dict[str, float] = defaultdict(float)
    n_by_symbol: dict[str, int] = defaultdict(int)
    for row in rows:
        symbol = row.get("symbol") or "<missing>"
        n_by_symbol[symbol] += 1
        pnl_by_symbol[symbol] += _cost_adjusted_pnl(row)
    positive = sorted((value for value in pnl_by_symbol.values() if value > 0), reverse=True)
    total_positive = sum(positive)
    counts = sorted(n_by_symbol.values(), reverse=True)
    return {
        "top_one_n_share": round(counts[0] / len(rows), 8) if rows else None,
        "top_three_n_share": round(sum(counts[:3]) / len(rows), 8) if rows else None,
        "top_one_positive_pnl_share": round(positive[0] / total_positive, 8) if positive else None,
        "top_three_positive_pnl_share": round(sum(positive[:3]) / total_positive, 8) if positive else None,
    }


def build_report(rows: list[dict[str, str]], *, seed: int = 2309, samples: int = 10_000) -> dict[str, Any]:
    records, source_rows, missing_ids = _final_records(rows)
    records = [row for row in records if not _is_technical_demo(row)]
    cells: dict[str, Any] = {}
    for small in (True, False):
        for mean_reversion in (True, False):
            name = f"small_{str(small).lower()}__mean_reversion_{str(mean_reversion).lower()}"
            group = [row for row in records if _small(row) is small and _mean_reversion(row) is mean_reversion]
            returns = [value for row in group if (value := _normalized_return(row)) is not None]
            cells[name] = _metrics(group)
            cells[name]["bootstrap_mean_normalized_return_95pct"] = _bootstrap_ci(
                returns, seed=seed, samples=samples
            )

    strategies: dict[str, list[dict[str, str]]] = defaultdict(list)
    weeks: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in records:
        strategies[row.get("strategy") or "<missing>"].append(row)
        weeks[_week(row)].append(row)
    eligible_strategies = {
        name: _band_comparison(group) for name, group in sorted(strategies.items())
        if sum(_small(row) for row in group) >= 30 and sum(not _small(row) for row in group) >= 30
    }
    eligible_weeks = {
        name: _band_comparison(group) for name, group in sorted(weeks.items())
        if sum(_small(row) for row in group) >= 20 and sum(not _small(row) for row in group) >= 20
    }
    aggregate = _band_comparison(records)
    small_mean = aggregate["small"]["mean_normalized_return"]
    larger_mean = aggregate["larger"]["mean_normalized_return"]
    aggregate_delta = small_mean - larger_mean if small_mean is not None and larger_mean is not None else None
    weekly_same_direction = sum(
        (comparison["small"]["mean_normalized_return"] - comparison["larger"]["mean_normalized_return"])
        * aggregate_delta > 0 for comparison in eligible_weeks.values()
    ) if aggregate_delta is not None else None
    small_rows = [row for row in records if _small(row)]
    mean_rows = [row for row in records if _mean_reversion(row)]
    return {
        "version": 1,
        "source_rows": source_rows,
        "missing_trade_ids": missing_ids,
        "final_records": len(records),
        "seed": seed,
        "bootstrap_samples": samples,
        "cells": cells,
        "aggregate_notional_comparison": aggregate,
        "eligible_strategy_comparisons": eligible_strategies,
        "eligible_week_comparisons": eligible_weeks,
        "eligible_week_count": len(eligible_weeks),
        "weekly_same_direction_count": weekly_same_direction,
        "small_notional_concentration": _concentration(small_rows),
        "mean_reversion_concentration": _concentration(mean_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.journal, newline="", encoding="utf-8") as source:
        report = build_report(list(csv.DictReader(source)))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "final_records": report["final_records"],
        "eligible_strategies": len(report["eligible_strategy_comparisons"]),
        "eligible_weeks": report["eligible_week_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
