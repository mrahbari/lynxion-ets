"""Read-only profitability monitor for a post-deployment prospective cohort.

This module never participates in order routing.  It only evaluates completed,
fully-attributable trades recorded after an explicit cohort boundary.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List

from infrastructure.results_tracking.edge_gate import EdgeGateThresholds, evaluate_edge_gate
from infrastructure.results_tracking.edge_ledger import compute_edge_records

REQUIRED_ATTRIBUTION_FIELDS = (
    "strategy", "regime", "confidence", "initial_stop_loss", "initial_take_profit", "risk_usdt", "r_multiple",
)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _pnl(row: Dict[str, str]) -> float:
    return float(row["pnl_usdt"])


def build_prospective_edge_report(
    rows: Iterable[Dict[str, str]], cohort_start: str
) -> Dict[str, Any]:
    """Evaluate closed rows after ``cohort_start`` and reject incomplete attribution.

    ``cohort_start`` is deliberately explicit.  A monitor must not silently mix
    historical trades created before the deployment that repaired attribution.
    """
    start = _parse_timestamp(cohort_start)
    cohort = [
        row for row in rows
        if row.get("exit_timestamp") and _parse_timestamp(row["entry_timestamp"]) >= start
    ]
    incomplete = [
        row for row in cohort
        if any(not row.get(field) for field in REQUIRED_ATTRIBUTION_FIELDS)
    ]
    complete = [row for row in cohort if row not in incomplete]

    report: Dict[str, Any] = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_start": start.isoformat(),
        "cohort_trade_count": len(cohort),
        "attributable_trade_count": len(complete),
        "incomplete_attribution_count": len(incomplete),
        "required_attribution_fields": list(REQUIRED_ATTRIBUTION_FIELDS),
        "mode": "SHADOW_READ_ONLY",
    }
    if incomplete:
        report.update({
            "verdict": "INSUFFICIENT_ATTRIBUTION",
            "summary": "Completed cohort contains trades without required decision metadata; edge evaluation withheld.",
            "cells": [],
        })
        return report

    pnls = [_pnl(row) for row in complete]
    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in complete:
        grouped[(row["strategy"], row["side"], row["regime"])] .append({
            "pnl": _pnl(row), "regime": row["regime"],
        })

    cells = []
    records = []
    for (strategy, side, regime), trades in sorted(grouped.items()):
        # Side is part of the candidate definition: do not allow profitable
        # shorts to mask unprofitable longs (or vice versa).
        [record] = compute_edge_records(trades, strategy=f"{strategy}:{side}", default_regime=regime)
        records.append(record)
        cells.append(record.to_dict())

    gate = evaluate_edge_gate(records, EdgeGateThresholds(min_trades=30))
    gross_profit = sum(value for value in pnls if value > 0)
    largest_win = max((value for value in pnls if value > 0), default=0.0)
    report.update({
        "verdict": gate.verdict,
        "summary": gate.summary,
        "overall": {
            "net_pnl": sum(pnls),
            "expectancy": sum(pnls) / len(pnls) if pnls else 0.0,
            "median_pnl": median(pnls) if pnls else 0.0,
            "win_rate": sum(value > 0 for value in pnls) / len(pnls) if pnls else 0.0,
            "largest_win_share_of_gross_profit": largest_win / gross_profit if gross_profit else 0.0,
        },
        "cells": cells,
        "gate": gate.to_dict(),
    })
    return report


def generate_prospective_edge_report(
    csv_path: str, cohort_start: str, output_path: str
) -> Dict[str, Any]:
    """Generate and persist a read-only prospective cohort report."""
    with open(csv_path, newline="", encoding="utf-8") as handle:
        report = build_prospective_edge_report(csv.DictReader(handle), cohort_start)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    return report
