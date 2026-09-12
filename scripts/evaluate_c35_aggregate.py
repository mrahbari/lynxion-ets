#!/usr/bin/env python3
"""Open C-35 aggregate economics only after every frozen minimum gate passes."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.c35_aggregate_math import (
        chronological_week_folds,
        daily_clustered_lower_bound,
        max_drawdown,
        mean,
        profit_factor,
    )
    from scripts.check_c35_unseal_gate import check_source_bound
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from c35_aggregate_math import (
        chronological_week_folds,
        daily_clustered_lower_bound,
        max_drawdown,
        mean,
        profit_factor,
    )
    from check_c35_unseal_gate import check_source_bound


PRIMARY = "net_return_primary_0_30pct"
STRESS = "net_return_stress_0_50pct"


def evaluate_verified_outcomes(
    outcomes: list[dict[str, Any]],
    *,
    bootstrap_samples: int = 10_000,
) -> dict[str, Any]:
    ordered = sorted(outcomes, key=lambda row: (int(row["exit_open_time"]), row["signal_key"]))
    primary = [float(row[PRIMARY]) for row in ordered]
    stress = [float(row[STRESS]) for row in ordered]
    pf = profit_factor(primary)
    folds = chronological_week_folds(ordered)
    fold_metrics = [{"n": len(fold), "expectancy": mean([float(row[PRIMARY]) for row in fold]) if fold else None} for fold in folds]
    side_values: dict[str, list[float]] = defaultdict(list)
    symbol_values: dict[str, list[float]] = defaultdict(list)
    for row in ordered:
        side_values[row["side"]].append(float(row[PRIMARY]))
        symbol_values[row["symbol"]].append(float(row[PRIMARY]))
    side_expectancy = {side: mean(side_values[side]) for side in ("LONG", "SHORT")}
    symbol_expectancy = {symbol: mean(values) for symbol, values in sorted(symbol_values.items())}
    symbol_pnl = {symbol: sum(values) for symbol, values in symbol_values.items()}
    positive_pnl = {symbol: value for symbol, value in symbol_pnl.items() if value > 0}
    total_positive = sum(positive_pnl.values())
    concentration = max(positive_pnl.values()) / total_positive if total_positive else 1.0
    bootstrap_lower = daily_clustered_lower_bound(ordered, samples=bootstrap_samples)
    gates = {
        "primary_expectancy": mean(primary) > 0,
        "profit_factor": pf is not None and pf > 1,
        "bootstrap_lower_bound": bootstrap_lower > 0,
        "both_sides_positive": all(value > 0 for value in side_expectancy.values()),
        "four_symbols_non_negative": sum(value >= 0 for value in symbol_expectancy.values()) >= 4,
        "positive_pnl_concentration": concentration <= 0.35,
        "max_drawdown": max_drawdown(primary) <= 0.20,
        "stress_expectancy": mean(stress) > 0,
        "chronological_folds": sum(
            metric["n"] >= 40 and metric["expectancy"] is not None and metric["expectancy"] > 0
            for metric in fold_metrics
        ) >= 3,
    }
    return {
        "candidate": "C-35",
        "aggregate_economics": "OPENED_AFTER_MINIMUM_GATE",
        "verdict": "KEEP_FOR_SEPARATE_VST_REVIEW" if all(gates.values()) else "REJECT",
        "n": len(ordered),
        "expectancy_primary": mean(primary),
        "profit_factor": "INFINITY" if pf is not None and math.isinf(pf) else pf,
        "bootstrap_95pct_lower": bootstrap_lower,
        "side_expectancy": side_expectancy,
        "symbol_expectancy": symbol_expectancy,
        "positive_pnl_symbol_concentration": concentration,
        "max_drawdown": max_drawdown(primary),
        "stress_expectancy_0_50pct": mean(stress),
        "folds": fold_metrics,
        "gates": gates,
    }


def evaluate(
    events: list[dict[str, Any]],
    candles: list[dict[str, Any]],
    funding: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
) -> dict[str, Any]:
    minimum = check_source_bound(events, candles, funding, coverage)
    if minimum["aggregate_economics"] == "SEALED":
        return minimum
    outcomes = [row for row in events if row.get("kind") == "OUTCOME"]
    return evaluate_verified_outcomes(outcomes)


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/research/c35"))
    args = parser.parse_args()
    root = args.root
    result = evaluate(
        _read(root / "signals.jsonl"), _read(root / "candles.jsonl"),
        _read(root / "funding.jsonl"), _read(root / "funding_coverage.jsonl"),
    )
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
