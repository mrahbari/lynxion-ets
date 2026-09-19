#!/usr/bin/env python3
"""Audit existing point-in-time data for a funding-settlement market-quality diagnostic."""

import argparse
import json
from pathlib import Path

import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT")


def range_summary(series, unit="s"):
    numeric = pd.to_numeric(series, errors="coerce").dropna().astype("int64")
    return {
        "records": int(len(numeric)),
        "start": pd.to_datetime(int(numeric.min()), unit=unit, utc=True).isoformat(),
        "end": pd.to_datetime(int(numeric.max()), unit=unit, utc=True).isoformat(),
    }


def audit(root):
    root = Path(root)
    symbols = {}
    for symbol in SYMBOLS:
        funding = pd.read_csv(root / f"data/research/c16/funding/{symbol}.csv", usecols=["timestamp"])
        flow = pd.read_csv(
            root / f"data/research/taker_flow/normalized/{symbol}.csv.gz",
            usecols=["timestamp"],
        )
        depth_path = root / f"data/research/bookdepth/normalized/{symbol}.csv.gz"
        depth = pd.read_csv(depth_path, nrows=1)
        depth_times = pd.read_csv(depth_path, usecols=["timestamp"])
        gaps = funding["timestamp"].diff().dropna().div(3600)
        symbols[symbol] = {
            "funding": range_summary(funding["timestamp"]),
            "funding_gap_hours": {
                str(float(key)): int(value) for key, value in gaps.value_counts().sort_index().items()
            },
            "flow": range_summary(flow["timestamp"]),
            "depth": range_summary(depth_times["timestamp"]),
            "depth_fields": [column for column in depth.columns if column != "timestamp"],
        }

    common_start = max(item["flow"]["start"] for item in symbols.values())
    common_end = min(item["flow"]["end"] for item in symbols.values())
    has_depth = all(item["depth_fields"] for item in symbols.values())
    actual_schedules = all(item["funding"]["records"] > 5000 for item in symbols.values())
    return {
        "lead": "FUNDING_SETTLEMENT_MARKET_QUALITY_CLOCK",
        "symbols": symbols,
        "common_flow_start": common_start,
        "common_flow_end": common_end,
        "actual_funding_timestamps_available": actual_schedules,
        "flow_15m_available": True,
        "depth_snapshot_available": has_depth,
        "spread_available": False,
        "receive_timestamp_available": False,
        "directional_edge_claimed": False,
        "verdict": "MINIMAL_DIAGNOSTIC_JUSTIFIED" if actual_schedules and has_depth else "INSUFFICIENT_DATA",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
