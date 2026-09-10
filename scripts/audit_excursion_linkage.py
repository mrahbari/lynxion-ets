#!/usr/bin/env python3
"""Link candle-excursion diagnostics to journal trades without guessing."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def _symbol(value: Any) -> str:
    return str(value or "").replace("-", "").upper()


def _side(value: Any) -> str:
    side = str(value or "").upper()
    return {"BUY": "LONG", "SELL": "SHORT"}.get(side, side)


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _key(row: dict[str, Any], *, diagnostic: bool) -> tuple[Any, ...]:
    return (
        _symbol(row.get("symbol")),
        _side(row.get("side")),
        row.get("entry_time" if diagnostic else "entry_timestamp"),
        _decimal(row.get("entry_price")),
        _decimal(row.get("quantity")),
    )


def final_journal_records(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_trade_id: dict[str, dict[str, str]] = {}
    for row in rows:
        trade_id = str(row.get("trade_id") or "").strip()
        if trade_id:
            by_trade_id[trade_id] = row
    return list(by_trade_id.values())


def assess_linkage(
    journal_rows: list[dict[str, str]], diagnostic_trades: list[dict[str, Any]]
) -> dict[str, Any]:
    records = final_journal_records(journal_rows)
    index: dict[tuple[Any, ...], list[dict[str, str]]] = defaultdict(list)
    for row in records:
        index[_key(row, diagnostic=False)].append(row)

    linked: list[dict[str, Any]] = []
    unmatched = ambiguous = missing_excursion = 0
    for trade in diagnostic_trades:
        candidates = index.get(_key(trade, diagnostic=True), [])
        if not candidates:
            unmatched += 1
            continue
        if len(candidates) != 1:
            ambiguous += 1
            continue
        if trade.get("mfe_roe_pct") is None or trade.get("mae_roe_pct") is None:
            missing_excursion += 1
            continue
        linked.append({
            "trade_id": candidates[0]["trade_id"],
            "symbol": candidates[0]["symbol"],
            "entry_timestamp": candidates[0]["entry_timestamp"],
        })

    sample_size = len(diagnostic_trades)
    return {
        "version": 1,
        "match_contract": [
            "canonical_symbol",
            "canonical_side",
            "exact_entry_timestamp",
            "exact_decimal_entry_price",
            "exact_decimal_quantity",
        ],
        "journal_final_records": len(records),
        "diagnostic_sample_size": sample_size,
        "unique_links": len(linked),
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        "missing_excursion": missing_excursion,
        "coverage": len(linked) / sample_size if sample_size else None,
        "linked_trades": linked,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True)
    parser.add_argument("--diagnostic", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.journal, newline="", encoding="utf-8") as source:
        journal_rows = list(csv.DictReader(source))
    diagnostic = json.loads(Path(args.diagnostic).read_text(encoding="utf-8"))
    report = assess_linkage(journal_rows, diagnostic.get("trades") or [])
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "diagnostic_sample_size", "unique_links", "unmatched", "ambiguous",
        "missing_excursion", "coverage",
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
