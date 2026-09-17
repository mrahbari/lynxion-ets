#!/usr/bin/env python3
"""Audit whether Lead A has a provenance-valid path plus realized exit dataset."""

import argparse
import csv
import glob
import json
from collections import Counter
from pathlib import Path


def read_jsonl(paths):
    rows = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def audit(root: Path):
    journal_path = root / "data/research/investor_release/trade_journal_baseline_v1.csv"
    with journal_path.open(encoding="utf-8", newline="") as handle:
        journal = list(csv.DictReader(handle))

    recent_path = root / "data/research/task0180/recent_bingx_exits_98.json"
    recent = json.loads(recent_path.read_text(encoding="utf-8"))

    event_paths = sorted(
        glob.glob(str(root / "data/observability/forward_exit/events/*.jsonl"))
    )
    events = read_jsonl(event_paths)
    event_types = Counter(row.get("event_type") for row in events)
    observed = [row for row in events if row.get("event_type") == "POSITION_OBSERVED"]
    position_keys = {row.get("position_key") for row in observed if row.get("position_key")}
    mark_observations = sum(row.get("price_source") == "MARK" for row in observed)
    exit_events = sum(
        event_types[name]
        for name in ("POSITION_CLOSED", "EXIT_FILLED", "STOP_TRIGGERED", "TAKE_PROFIT_FILLED")
    )

    candle_dir = root / "data/history/raw/1m"
    journal_symbols = {row["symbol"] for row in journal if row.get("symbol")}
    candle_symbols = {
        path.stem.replace("-", "") for path in candle_dir.glob("*-USDT.csv")
    }

    gates = {
        "closed_trade_outcomes_present": bool(journal) and bool(recent.get("trades")),
        "authoritative_mark_path_present": mark_observations > 0,
        "forward_exit_fill_events_present": exit_events > 0,
        "closed_trade_candle_market_identity_declared": False,
        "single_dataset_joins_path_to_realized_exit": False,
    }
    ready = all(gates.values())
    return {
        "lead": "A_EDGE_RETENTION_PROFIT_GIVEBACK",
        "journal": {
            "rows": len(journal),
            "symbols": len(journal_symbols),
            "symbols_with_local_1m_file": len(journal_symbols & candle_symbols),
            "has_realized_exit": True,
            "path_market_identity": "UNKNOWN",
        },
        "recent_bingx_diagnostic": {
            "rows": len(recent.get("trades", [])),
            "historical_leverage": "INFERRED_OR_MISSING",
            "path_source": "PUBLIC_1M_CANDLES",
            "confirmatory_use": False,
        },
        "forward_exit_ledger": {
            "files": len(event_paths),
            "events": len(events),
            "position_keys": len(position_keys),
            "position_observations": len(observed),
            "mark_price_observations": mark_observations,
            "exit_fill_events": exit_events,
            "event_types": dict(sorted(event_types.items())),
        },
        "readiness_gates": gates,
        "verdict": (
            "READY_FOR_DESCRIPTIVE_PATH_ANALYSIS"
            if ready
            else "INSUFFICIENT_PROVENANCE"
        ),
        "next": (
            "analyze_state before giveback"
            if ready
            else "collect one unopened cohort joining authoritative mark observations to realized exit fills"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
