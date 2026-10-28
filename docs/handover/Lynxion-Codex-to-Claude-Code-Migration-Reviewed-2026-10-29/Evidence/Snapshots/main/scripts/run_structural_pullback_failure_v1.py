#!/usr/bin/env python3
"""Offline descriptive V1 candidate run from a hash-qualified local M15 panel.

No network, broker, order, future-return, or parameter-search dependency.
"""
import argparse
import csv
import hashlib
import json
import shlex
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from domain.research.structural_pullback_failure_v1 import ResearchBar, detect
from infrastructure.replay.historical_closed_bar_source import (
    ClosedBar, HistoricalClosedBarSource,
)


INTERVAL = timedelta(minutes=15)
START = datetime(2023, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(days=7)
ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
EXPECTED_SYMBOLS = ("ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualified_panel(source: Path):
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("endpoint") != ENDPOINT or manifest.get("interval") != "15m"
            or manifest.get("gate", {}).get("verdict") != "KEEP"
            or tuple(sorted(manifest.get("symbols", {}))) != EXPECTED_SYMBOLS):
        raise ValueError("DATA_SOURCE_NOT_QUALIFIED: manifest source/schema/gate")
    for symbol in EXPECTED_SYMBOLS:
        meta = manifest["symbols"][symbol]
        path = source / f"{symbol}.csv"
        if digest(path) != meta.get("sha256") or any(meta.get(key) != 0 for key in
            ("duplicate_count", "missing_interval_count", "nonpositive_count",
             "ohlc_violation_count", "out_of_range_count")):
            raise ValueError(f"DATA_SOURCE_NOT_QUALIFIED: {symbol} hash/integrity")
    return manifest, digest(manifest_path)


def load_window(path: Path, symbol: str):
    selected = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["timestamp", "open", "high", "low", "close", "volume"]:
            raise ValueError(f"DATA_SOURCE_NOT_QUALIFIED: {symbol} CSV schema")
        for row in reader:
            seconds = int(row["timestamp"])
            opened = datetime.fromtimestamp(seconds, timezone.utc)
            if opened < START or opened >= END:
                continue
            if seconds % 900:
                raise ValueError("unaligned M15 open timestamp")
            selected.append(ClosedBar(symbol, INTERVAL, opened, opened + INTERVAL,
                                      *(float(row[key]) for key in
                                        ("open", "high", "low", "close", "volume"))))
    if len(selected) != 7 * 24 * 4:
        raise ValueError(f"DATA_SOURCE_NOT_QUALIFIED: incomplete bounded window {symbol}")
    source = HistoricalClosedBarSource(selected)
    visible = tuple(source.completed_through(END))
    return tuple(ResearchBar(bar.symbol, bar.timeframe, bar.open_time,
                             bar.close_time, bar.open, bar.high, bar.low,
                             bar.close, bar.volume) for bar in visible)


def encode(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, tuple):
        return [encode(x) for x in value]
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    return value


def run(source: Path, contract: Path, output: Path):
    metadata, manifest_sha = qualified_panel(source)
    contract_sha = digest(contract)
    candidates = []
    by_symbol = {}
    for symbol in EXPECTED_SYMBOLS:
        path = source / f"{symbol}.csv"
        observed = load_window(path, symbol)
        events = detect(observed, contract_sha256=contract_sha,
                        dataset_sha256=digest(path), as_of=END)
        candidates.extend(events)
        by_symbol[symbol] = {"bars": len(observed), "candidates": len(events),
                             "dataset_sha256": digest(path)}
    candidates.sort(key=lambda c: (c.decision_time, c.symbol, c.candidate_id))
    ids = [c.candidate_id for c in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate ID")
    output.mkdir(parents=True, exist_ok=True)
    records = output / "candidates.jsonl"
    rendered = "".join(json.dumps(encode(asdict(item)), sort_keys=True,
                                  separators=(",", ":")) + "\n" for item in candidates)
    if records.exists():
        if records.read_text(encoding="utf-8") != rendered:
            raise ValueError("candidate output already exists with different bytes")
    else:
        records.write_text(rendered, encoding="utf-8")
    code_commit = subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"],
                                          text=True).strip()
    run_manifest = {
        "classification": "DESCRIPTIVE_DEVELOPMENT_ONLY_NOT_EDGE",
        "source": ENDPOINT, "source_manifest_sha256": manifest_sha,
        "source_task": metadata["task"], "contract_sha256": contract_sha,
        "code_commit": code_commit, "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(), "window_rule":
        "first full seven UTC days of the six-symbol aligned panel; chosen before candidate run",
        "symbols": by_symbol, "candidate_count": len(candidates),
        "bullish_count": sum(c.direction.startswith("BULLISH") for c in candidates),
        "bearish_count": sum(c.direction.startswith("BEARISH") for c in candidates),
        "candidate_records_sha256": digest(records),
        "command": "PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 " + " ".join(
            shlex.quote(part) for part in
            (sys.executable, "scripts/run_structural_pullback_failure_v1.py",
             "--source", str(source), "--contract", str(contract),
             "--output", str(output))),
        "limitations": ["raw exchange response pages unavailable for independent wire-level verification",
                        "source panel reused from previously opened C06 studies; development-only",
                        "no point-in-time exchange-wide tradable universe",
                        "no HTF context or future outcomes inspected"],
    }
    manifest_path = output / "candidate_manifest.json"
    manifest_bytes = json.dumps(run_manifest, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists():
        if manifest_path.read_text(encoding="utf-8") != manifest_bytes:
            raise ValueError("candidate manifest already exists with different bytes")
    else:
        manifest_path.write_text(manifest_bytes, encoding="utf-8")
    return run_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.contract, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
