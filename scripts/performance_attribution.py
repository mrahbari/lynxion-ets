#!/usr/bin/env python3
"""Cost-adjusted performance attribution for the final record of each trade ID."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional


def _number(row: Dict[str, str], field: str) -> float:
    try:
        return float(row.get(field) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _final_records(rows: Iterable[Dict[str, str]]) -> tuple[list[Dict[str, str]], int, int]:
    by_id: Dict[str, Dict[str, str]] = {}
    source_rows = 0
    missing_ids = 0
    for row in rows:
        source_rows += 1
        trade_id = (row.get("trade_id") or "").strip()
        if not trade_id:
            missing_ids += 1
            continue
        by_id[trade_id] = row
    return list(by_id.values()), source_rows, missing_ids


def _cost_adjusted_pnl(row: Dict[str, str]) -> float:
    # BingX records realized profit and commission separately; commission is signed.
    return _number(row, "pnl_usdt") + _number(row, "fees_usdt")


def _confidence_bucket(row: Dict[str, str]) -> str:
    raw = row.get("confidence")
    if raw in (None, ""):
        return "<missing>"
    value = _number(row, "confidence")
    if value < 0.50:
        return "<0.50"
    if value < 0.60:
        return "0.50-0.60"
    if value < 0.70:
        return "0.60-0.70"
    if value < 0.80:
        return "0.70-0.80"
    return ">=0.80"


def _duration_bucket(row: Dict[str, str]) -> str:
    raw = row.get("duration_seconds")
    if raw in (None, ""):
        return "<missing>"
    seconds = _number(row, "duration_seconds")
    if seconds < 15 * 60:
        return "<15m"
    if seconds < 60 * 60:
        return "15m-1h"
    if seconds < 4 * 60 * 60:
        return "1h-4h"
    if seconds < 24 * 60 * 60:
        return "4h-24h"
    return ">=24h"


def _metrics(rows: list[Dict[str, str]]) -> Dict[str, Any]:
    values = [_cost_adjusted_pnl(row) for row in rows]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    average_win = gross_profit / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0

    equity = peak = max_drawdown = 0.0
    chronological = sorted(
        rows,
        key=lambda row: row.get("exit_timestamp") or "",
    )
    for row in chronological:
        equity += _cost_adjusted_pnl(row)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    return {
        "n": len(rows),
        "recorded_pnl_usdt": round(sum(_number(row, "pnl_usdt") for row in rows), 8),
        "fees_usdt": round(sum(_number(row, "fees_usdt") for row in rows), 8),
        "cost_adjusted_pnl_usdt": round(sum(values), 8),
        "expectancy_usdt": round(sum(values) / len(values), 8) if values else None,
        "profit_factor": round(gross_profit / gross_loss, 8) if gross_loss else None,
        "win_rate": round(len(wins) / len(values), 8) if values else None,
        "average_win_usdt": round(average_win, 8) if wins else None,
        "average_loss_usdt": round(average_loss, 8) if losses else None,
        "payoff_ratio": round(average_win / abs(average_loss), 8) if wins and losses else None,
        "max_drawdown_usdt": round(max_drawdown, 8),
        "average_entry_notional_usdt": round(
            sum(_number(row, "entry_price") * _number(row, "quantity") for row in rows) / len(rows), 8
        ) if rows else None,
        "execution_unwinds": sum((row.get("is_execution_unwind") or "").lower() == "true" for row in rows),
    }


def _group(rows: list[Dict[str, str]], key: Callable[[Dict[str, str]], str]) -> Dict[str, Any]:
    grouped: Dict[str, list[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[key(row) or "<blank>"].append(row)
    return {name: _metrics(group) for name, group in sorted(grouped.items())}


def build_report(
    path: str,
    cohort_start: Optional[str] = None,
    cohort_timestamp_field: str = "entry_timestamp",
) -> Dict[str, Any]:
    with open(path, newline="", encoding="utf-8") as source:
        records, source_rows, missing_ids = _final_records(csv.DictReader(source))
    start = _timestamp(cohort_start) if cohort_start else None
    cohort = [
        row for row in records
        if start is None or (
            row.get(cohort_timestamp_field)
            and _timestamp(row[cohort_timestamp_field]) >= start
        )
    ]
    required = ("strategy", "side", "entry_timestamp", "exit_timestamp", "pnl_usdt", "fees_usdt")
    return {
        "version": 1,
        "journal_path": str(Path(path)),
        "cohort_start": cohort_start,
        "cohort_timestamp_field": cohort_timestamp_field,
        "data_quality": {
            "source_rows": source_rows,
            "unique_trade_ids": len(records),
            "duplicate_rows": source_rows - len(records) - missing_ids,
            "records_without_trade_id": missing_ids,
            "cohort_trade_ids": len(cohort),
            "rows_missing_required_fields": sum(any(row.get(field) in (None, "") for field in required) for row in cohort),
            "rows_missing_confidence": sum(row.get("confidence") in (None, "") for row in cohort),
            "rows_missing_regime": sum(row.get("regime") in (None, "") for row in cohort),
            "rows_missing_initial_sl": sum(_number(row, "initial_stop_loss") <= 0 for row in cohort),
            "rows_missing_initial_tp": sum(_number(row, "initial_take_profit") <= 0 for row in cohort),
            "mfe_available": False,
            "mae_available": False,
        },
        "overall": _metrics(cohort),
        "by_strategy": _group(cohort, lambda row: row.get("strategy") or "<blank>"),
        "by_symbol": _group(cohort, lambda row: row.get("symbol") or "<blank>"),
        "by_side": _group(cohort, lambda row: row.get("side") or "<blank>"),
        "by_timeframe": _group(cohort, lambda row: row.get("timeframe") or "<blank>"),
        "by_regime": _group(cohort, lambda row: row.get("regime") or "<missing>"),
        "by_confidence_bucket": _group(cohort, _confidence_bucket),
        "by_duration_bucket": _group(cohort, _duration_bucket),
        "by_exit_reason": _group(cohort, lambda row: row.get("exit_reason") or "<blank>"),
        "by_position_size_bucket": _group(
            cohort,
            lambda row: "<=$25" if _number(row, "entry_price") * _number(row, "quantity") <= 25
            else "$25-$100" if _number(row, "entry_price") * _number(row, "quantity") <= 100
            else "$100-$1000" if _number(row, "entry_price") * _number(row, "quantity") <= 1000
            else ">$1000",
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", default="data/trade_journal.csv")
    parser.add_argument("--cohort-start", help="Inclusive ISO-8601 cohort boundary")
    parser.add_argument(
        "--cohort-timestamp-field",
        choices=("entry_timestamp", "exit_timestamp"),
        default="entry_timestamp",
        help="Timestamp used to admit a trade to the cohort (default: entry_timestamp)",
    )
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()
    report = build_report(args.journal, args.cohort_start, args.cohort_timestamp_field)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
