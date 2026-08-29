#!/usr/bin/env python3
"""Read-only trade-journal summary with explicit final-record deduplication."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def _number(row: Dict[str, str], field: str) -> float:
    try:
        return float(row.get(field) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _final_records(rows: Iterable[Dict[str, str]]) -> tuple[list[Dict[str, str]], int]:
    by_id: Dict[str, Dict[str, str]] = {}
    records_without_id = 0
    for row in rows:
        trade_id = row.get("trade_id", "").strip()
        if not trade_id:
            records_without_id += 1
            continue
        by_id[trade_id] = row
    return list(by_id.values()), records_without_id


def build_report(path: str, cohort_start: Optional[str] = None) -> Dict[str, Any]:
    """Read the CSV and summarize its final record per trade ID without modifying it."""
    with open(path, newline="", encoding="utf-8") as source:
        source_rows = list(csv.DictReader(source))

    records, records_without_id = _final_records(source_rows)
    start = _parse_timestamp(cohort_start) if cohort_start else None
    cohort = [
        row for row in records
        if start is None or (row.get("exit_timestamp") and _parse_timestamp(row["exit_timestamp"]) >= start)
    ]
    pnl = [_number(row, "pnl_usdt") for row in cohort]
    wins = [value for value in pnl if value > 0]
    losses = [value for value in pnl if value < 0]
    loss_total = abs(sum(losses))

    return {
        "journal_path": str(Path(path)),
        "cohort_start": cohort_start,
        "source_rows": len(source_rows),
        "unique_trade_ids": len(records),
        "duplicate_rows": len(source_rows) - len(records) - records_without_id,
        "records_without_trade_id": records_without_id,
        "cohort_trade_ids": len(cohort),
        "net_pnl_usdt": round(sum(pnl), 8),
        "fees_usdt": round(sum(_number(row, "fees_usdt") for row in cohort), 8),
        "wins": len(wins),
        "losses": len(losses),
        "profit_factor": round(sum(wins) / loss_total, 8) if loss_total else None,
        "expectancy_usdt": round(sum(pnl) / len(pnl), 8) if pnl else None,
        "by_side": dict(Counter(row.get("side") or "<blank>" for row in cohort)),
        "by_exit_reason": dict(Counter(row.get("exit_reason") or "<blank>" for row in cohort)),
        "missing_initial_stop_loss": sum(_number(row, "initial_stop_loss") <= 0 for row in cohort),
        "missing_initial_take_profit": sum(_number(row, "initial_take_profit") <= 0 for row in cohort),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", default="data/trade_journal.csv")
    parser.add_argument("--cohort-start", help="Inclusive ISO-8601 exit timestamp boundary")
    args = parser.parse_args()
    print(json.dumps(build_report(args.journal, args.cohort_start), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
