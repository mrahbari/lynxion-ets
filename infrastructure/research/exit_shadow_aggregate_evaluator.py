"""Deterministic aggregate evaluator sealed behind frozen coverage admission."""

from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Any

from infrastructure.research.exit_shadow_aggregate_protocol import (
    AGGREGATE_PROTOCOL,
    admit_aggregate_request,
)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _profit_factor(values: list[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    return gains / losses if losses else None


def _drawdown(values: list[float]) -> float:
    equity = peak = worst = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _expected_shortfall(values: list[float]) -> float:
    count = max(1, math.ceil(len(values) * AGGREGATE_PROTOCOL["expected_shortfall_tail_fraction"]))
    return _mean(sorted(values)[:count])


def _bootstrap_lower(deltas: list[float]) -> float:
    rng = random.Random(AGGREGATE_PROTOCOL["bootstrap_seed"])
    estimates = [
        _mean([deltas[rng.randrange(len(deltas))] for _ in deltas])
        for _ in range(AGGREGATE_PROTOCOL["bootstrap_resamples"])
    ]
    estimates.sort()
    alpha = (1.0 - AGGREGATE_PROTOCOL["confidence_level"]) / 2.0
    return estimates[math.floor(alpha * (len(estimates) - 1))]


def evaluate_shadow_aggregates(
    coverage: dict[str, Any], records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Open frozen aggregate metrics only after exact coverage admission."""
    admission = admit_aggregate_request(coverage, records, protocol=AGGREGATE_PROTOCOL)
    if admission.get("eligible") is not True:
        return {"verdict": "COLLECTING", "reason": admission["reason"], "metrics": None}

    ordered = sorted(
        records,
        key=lambda row: datetime.fromisoformat(row["terminal_time_utc"].replace("Z", "+00:00")),
    )
    numeric_fields = [
        "baseline_primary_net_roe_pct", "candidate_primary_net_roe_pct",
        "baseline_stress_net_roe_pct", "candidate_stress_net_roe_pct",
    ]
    for row in ordered:
        if any(
            isinstance(row[field], bool) or not isinstance(row[field], (int, float))
            or not math.isfinite(row[field]) for field in numeric_fields
        ):
            raise ValueError("aggregate economics must be finite numeric")

    baseline = [row["baseline_primary_net_roe_pct"] for row in ordered]
    candidate = [row["candidate_primary_net_roe_pct"] for row in ordered]
    baseline_stress = [row["baseline_stress_net_roe_pct"] for row in ordered]
    candidate_stress = [row["candidate_stress_net_roe_pct"] for row in ordered]
    deltas = [right - left for left, right in zip(baseline, candidate)]
    stress_deltas = [right - left for left, right in zip(baseline_stress, candidate_stress)]

    folds = []
    for fold in range(4):
        rows = [row for index, row in enumerate(ordered) if index * 4 // len(ordered) == fold]
        a = [row["baseline_primary_net_roe_pct"] for row in rows]
        b = [row["candidate_primary_net_roe_pct"] for row in rows]
        folds.append({
            "baseline_expectancy": _mean(a), "candidate_expectancy": _mean(b),
            "candidate_profit_factor": _profit_factor(b),
        })

    side_delta = {
        side: _mean([
            row["candidate_primary_net_roe_pct"] - row["baseline_primary_net_roe_pct"]
            for row in ordered if row["side"] == side
        ]) for side in ("LONG", "SHORT")
    }
    symbol_contribution: dict[str, float] = {}
    for row, delta in zip(ordered, deltas):
        symbol_contribution[row["symbol"]] = symbol_contribution.get(row["symbol"], 0.0) + delta
    top_symbol = max(symbol_contribution, key=symbol_contribution.get)
    excluded_delta = _mean([
        delta for row, delta in zip(ordered, deltas) if row["symbol"] != top_symbol
    ])
    baseline_es = _expected_shortfall(baseline)
    candidate_es = _expected_shortfall(candidate)
    candidate_pf = _profit_factor(candidate)
    fold_passes = sum(
        fold["candidate_expectancy"] > 0
        and (fold["candidate_profit_factor"] is None or fold["candidate_profit_factor"] > 1.10)
        for fold in folds
    )
    bootstrap_lower = _bootstrap_lower(deltas)
    gates = {
        "paired_mean_improvement": _mean(deltas) > 0,
        "bootstrap_lower_bound": bootstrap_lower > 0,
        "aggregate_expectancy": _mean(candidate) > 0,
        "aggregate_profit_factor": candidate_pf is None or candidate_pf > 1.10,
        "three_of_four_folds": fold_passes >= 3,
        "no_worse_negative_fold": all(
            not (fold["candidate_expectancy"] < 0 and fold["candidate_expectancy"] < fold["baseline_expectancy"])
            for fold in folds
        ),
        "stress_improvement": _mean(stress_deltas) > 0,
        "both_sides_improve": all(value > 0 for value in side_delta.values()),
        "top_symbol_exclusion": excluded_delta > 0,
        "drawdown_not_worse": _drawdown(candidate) <= _drawdown(baseline),
        "tail_not_materially_worse": candidate_es >= baseline_es - 0.10 * abs(baseline_es),
    }
    metrics = {
        "paired_mean_delta": _mean(deltas),
        "bootstrap_ci_lower": bootstrap_lower,
        "candidate_expectancy": _mean(candidate),
        "candidate_profit_factor": candidate_pf,
        "folds": folds,
        "side_delta": side_delta,
        "top_excluded_symbol": top_symbol,
        "top_symbol_excluded_delta": excluded_delta,
        "baseline_drawdown": _drawdown(baseline),
        "candidate_drawdown": _drawdown(candidate),
        "baseline_expected_shortfall": baseline_es,
        "candidate_expected_shortfall": candidate_es,
        "stress_mean_delta": _mean(stress_deltas),
    }
    return {
        "verdict": "KEEP_FOR_SEPARATE_DEPLOYMENT_REVIEW" if all(gates.values()) else "REJECT",
        "reason": None, "gates": gates, "metrics": metrics,
    }
