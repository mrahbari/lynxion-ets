#!/usr/bin/env python3
"""Freeze Lead-B dates from integrity metadata without reading flow or returns."""

import argparse
import json
from datetime import date
from pathlib import Path


def freeze(root: Path):
    base = root / "data/research/btc_aggtrades"
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    days = manifest.get("days", {})
    selected = []
    for year in (2024, 2025):
        for month in range(1, 13):
            prefix = f"{year:04d}-{month:02d}-"
            eligible = []
            for day, record in days.items():
                if not day.startswith(prefix) or record.get("rows") != 96:
                    continue
                raw_path = base / "raw" / f"BTCUSDT-aggTrades-{day}.zip"
                if raw_path.is_file():
                    eligible.append(day)
            if not eligible:
                raise ValueError(f"no complete raw day for {prefix}")
            selected.append(min(eligible))
    return {
        "candidate": "LEAD_B_QUARTER_HOUR_REPLICATION",
        "created_without_outcome_access": True,
        "selection_rule": "earliest complete UTC day with raw ZIP in each month",
        "date_range": [str(date(2024, 1, 1)), str(date(2025, 12, 31))],
        "selected_dates": selected,
        "selected_count": len(selected),
        "folds": {
            "2024_H1": [day for day in selected if "2024-01" <= day <= "2024-06-99"],
            "2024_H2": [day for day in selected if "2024-07" <= day <= "2024-12-99"],
            "2025_H1": [day for day in selected if "2025-01" <= day <= "2025-06-99"],
            "2025_H2": [day for day in selected if "2025-07" <= day <= "2025-12-99"],
        },
        "opening_window_seconds": [0, 10],
        "control_offsets_seconds": [300, 600],
        "future_horizons_hours": [4, 8, 12],
        "minimum_passing_days": 20,
        "status": "FROZEN_BEFORE_OUTCOMES",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze(args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
