#!/usr/bin/env python3
"""Audit whether retained BTC aggTrade data can resolve the Lead-B first-seconds window."""

import argparse
import gzip
import json
import zipfile
from pathlib import Path


def first_timestamps(path: Path, limit=3):
    values = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
        timestamp_index = header.index("timestamp")
        for line in handle:
            if line.strip():
                values.append(int(float(line.split(",")[timestamp_index])))
                if len(values) == limit:
                    break
    return header, values


def first_raw_timestamps(path: Path, limit=3):
    values = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != 1:
            return [], []
        with archive.open(names[0]) as raw:
            header = raw.readline().decode("utf-8").strip().split(",")
            timestamp_index = header.index("transact_time")
            for line in raw:
                if line.strip():
                    values.append(int(line.decode("utf-8").split(",")[timestamp_index]))
                    if len(values) == limit:
                        break
    return header, values


def audit(root: Path):
    base = root / "data/research/btc_aggtrades"
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    daily = sorted((base / "daily").glob("*.csv.gz"))
    header, sample_timestamps = first_timestamps(daily[0]) if daily else ([], [])
    intervals = [b - a for a, b in zip(sample_timestamps, sample_timestamps[1:])]
    days = manifest.get("days", {})
    raw_rows = sum(day.get("checks", {}).get("raw_rows", 0) for day in days.values())
    normalized_rows = sum(day.get("rows", 0) for day in days.values())
    raw_archives = sorted((base / "raw").glob("*.zip"))
    raw_header, raw_timestamps_ms = (
        first_raw_timestamps(raw_archives[0]) if raw_archives else ([], [])
    )
    raw_deltas_ms = [b - a for a, b in zip(raw_timestamps_ms, raw_timestamps_ms[1:])]
    minimum_interval = min(intervals) if intervals else None
    can_resolve_ten_seconds = bool(raw_archives) and "transact_time" in raw_header
    return {
        "lead": "B_QUARTER_HOUR_CLOCK_PHASE_ORDER_FLOW",
        "venue": "BINANCE_USDT_PERPETUAL",
        "symbol": "BTCUSDT",
        "manifest_days": len(days),
        "retained_daily_files": len(daily),
        "manifest_raw_rows_processed": raw_rows,
        "manifest_normalized_rows": normalized_rows,
        "retained_columns": header,
        "sample_timestamp_deltas_seconds": intervals,
        "retained_resolution_seconds": minimum_interval,
        "raw_archives_retained": len(raw_archives),
        "raw_columns": raw_header,
        "sample_raw_timestamp_deltas_ms": raw_deltas_ms,
        "first_10_seconds_resolvable": can_resolve_ten_seconds,
        "four_to_twelve_hour_outcomes_resolvable": bool(daily),
        "verdict": (
            "READY_FOR_REPLICATION_DIAGNOSTIC"
            if can_resolve_ten_seconds
            else "INSUFFICIENT_TEMPORAL_RESOLUTION"
        ),
        "next": (
            "run clock-phase replication"
            if can_resolve_ten_seconds
            else "acquire a tiny raw-aggTrade sample only after freezing the contract"
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
