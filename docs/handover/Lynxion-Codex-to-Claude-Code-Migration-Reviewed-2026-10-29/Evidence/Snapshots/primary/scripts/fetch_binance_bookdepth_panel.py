#!/usr/bin/env python3
"""Fetch and validate the frozen TASK-0109 Binance Futures book-depth archive."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

import requests


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
START = date(2023, 1, 1)
END = date(2026, 8, 29)
S3_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DATA_URL = "https://data.binance.vision/"
LEVELS = (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5)
EXPECTED_COLUMNS = ("timestamp", "percentage", "depth", "notional")
DATE_PATTERN = re.compile(r"-bookDepth-(\d{4}-\d{2}-\d{2})\.zip$")


def _common():
    path = Path(__file__).with_name("fetch_binance_oi_metrics_panel.py")
    spec = importlib.util.spec_from_file_location("archive_common", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def list_archives(symbol: str, start: date = START, end: date = END,
                  get: Callable[..., Any] = requests.get) -> list[str]:
    prefix = f"data/futures/um/daily/bookDepth/{symbol}/"
    keys: list[str] = []
    token = None
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": 1000}
        if token:
            params["continuation-token"] = token
        response = get(S3_LIST_URL, params=params, timeout=30)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        for item in root.findall("s3:Contents", namespace):
            key = item.findtext("s3:Key", namespaces=namespace) or ""
            match = DATE_PATTERN.search(key)
            if match and start <= date.fromisoformat(match.group(1)) <= end:
                keys.append(key)
        truncated = root.findtext("s3:IsTruncated", default="false", namespaces=namespace) == "true"
        if not truncated:
            break
        token = root.findtext("s3:NextContinuationToken", namespaces=namespace)
        if not token:
            raise ValueError(f"{symbol}: truncated listing without continuation token")
    return sorted(set(keys))


def download_archive(key: str, raw_root: Path,
                     get: Callable[..., Any] = requests.get) -> dict[str, Any]:
    """Download a bookDepth archive into its symbol directory.

    TASK-0109 originally reused the metrics downloader, whose filename parser is
    specific to ``-metrics-``.  The legacy lookup below makes the correction
    resumable for files already verified by that first local run.
    """
    common = _common()
    filename = Path(key).name
    symbol = filename.split("-bookDepth-", 1)[0]
    target = raw_root / symbol / filename
    checksum_response = get(DATA_URL + key + ".CHECKSUM", timeout=30)
    checksum_response.raise_for_status()
    expected = common.expected_checksum(checksum_response.text, filename)
    legacy = raw_root / filename / filename
    for cached in (target, legacy):
        if cached.exists() and hashlib.sha256(cached.read_bytes()).hexdigest() == expected:
            if cached != target:
                target.parent.mkdir(parents=True, exist_ok=True)
                cached.replace(target)
            return {"key": key, "sha256": expected, "bytes": target.stat().st_size,
                    "cached": True}
    response = get(DATA_URL + key, timeout=60)
    response.raise_for_status()
    payload = response.content
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError(f"{key}: checksum mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(target)
    return {"key": key, "sha256": actual, "bytes": len(payload), "cached": False}


def parse_archive(path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    checks = {"raw_rows": 0, "complete_snapshots": 0, "incomplete_snapshots": 0,
              "exact_duplicates": 0, "conflicting_duplicates": 0, "schema_violations": 0,
              "level_violations": 0, "extra_level_rows": 0, "numeric_violations": 0}
    snapshots: dict[str, dict[int, tuple[float, float]]] = {}
    raw_values: dict[tuple[str, int], tuple[float, float]] = {}
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected one CSV member")
        with archive.open(members[0]) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8"))
            if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
                checks["schema_violations"] += 1
                return [], checks
            for row in reader:
                checks["raw_rows"] += 1
                try:
                    level_value = float(row["percentage"])
                    depth, notional = float(row["depth"]), float(row["notional"])
                    if not math.isfinite(level_value):
                        checks["level_violations"] += 1
                        continue
                    if not level_value.is_integer():
                        checks["extra_level_rows"] += 1
                        continue
                    level = int(level_value)
                    if level not in LEVELS:
                        checks["level_violations"] += 1
                        continue
                    if not all(math.isfinite(value) and value >= 0 for value in (depth, notional)):
                        checks["numeric_violations"] += 1
                        continue
                except (TypeError, ValueError):
                    checks["numeric_violations"] += 1
                    continue
                key = (row["timestamp"], level)
                value = (depth, notional)
                previous = raw_values.get(key)
                if previous is not None:
                    if previous == value:
                        checks["exact_duplicates"] += 1
                    else:
                        checks["conflicting_duplicates"] += 1
                    continue
                raw_values[key] = value
                snapshots.setdefault(row["timestamp"], {})[level] = value
    complete = []
    for timestamp in sorted(snapshots):
        levels = snapshots[timestamp]
        if set(levels) != set(LEVELS):
            checks["incomplete_snapshots"] += 1
            continue
        epoch = int(datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc).timestamp())
        complete.append({"timestamp": epoch, "levels": levels})
    checks["complete_snapshots"] = len(complete)
    return complete, checks


def downsample_five_minutes(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_bucket: dict[int, dict[str, Any]] = {}
    for snapshot in snapshots:
        bucket = int(snapshot["timestamp"]) // 300
        if bucket not in by_bucket or snapshot["timestamp"] > by_bucket[bucket]["timestamp"]:
            by_bucket[bucket] = snapshot
    return [by_bucket[key] for key in sorted(by_bucket)]


def normalized_columns() -> list[str]:
    columns = ["timestamp"]
    for level in LEVELS:
        label = f"m{abs(level)}" if level < 0 else f"p{level}"
        columns.extend((f"depth_{label}", f"notional_{label}"))
    return columns


def normalize_symbol(symbol: str, records: list[dict[str, Any]], raw_root: Path,
                     normalized_root: Path) -> dict[str, Any]:
    totals = {"archives": len(records), "raw_rows": 0, "complete_snapshots": 0,
              "incomplete_snapshots": 0, "normalized_rows": 0, "exact_duplicates": 0,
              "conflicting_duplicates": 0, "schema_violations": 0, "level_violations": 0,
              "extra_level_rows": 0, "numeric_violations": 0,
              "missing_five_minute_buckets": 0}
    target = normalized_root / f"{symbol}.csv.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    first = last = previous_bucket = None
    with gzip.open(temporary, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(normalized_columns())
        for record in sorted(records, key=lambda item: item["key"]):
            path = raw_root / symbol / Path(record["key"]).name
            snapshots, checks = parse_archive(path)
            for key, value in checks.items():
                totals[key] += value
            for snapshot in downsample_five_minutes(snapshots):
                timestamp = int(snapshot["timestamp"])
                bucket = timestamp // 300
                if previous_bucket is not None and bucket > previous_bucket + 1:
                    totals["missing_five_minute_buckets"] += bucket - previous_bucket - 1
                previous_bucket = bucket
                first = timestamp if first is None else first
                last = timestamp
                row: list[Any] = [timestamp]
                for level in LEVELS:
                    row.extend(snapshot["levels"][level])
                writer.writerow(row)
                digest.update((",".join(map(str, row)) + "\n").encode())
                totals["normalized_rows"] += 1
    temporary.replace(target)
    totals.update({"first_timestamp": first, "last_timestamp": last,
                   "normalized_sha256": digest.hexdigest(), "normalized_file": str(target)})
    return totals


def build(output_root: Path, workers: int = 16, symbols: tuple[str, ...] = SYMBOLS,
          start: date = START, end: date = END) -> dict[str, Any]:
    common = _common()
    raw_root, normalized_root = output_root / "raw", output_root / "normalized"
    listings = {symbol: list_archives(symbol, start, end) for symbol in symbols}
    records: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    jobs = [(symbol, key) for symbol, keys in listings.items() for key in keys]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_archive, key, raw_root): symbol for symbol, key in jobs}
        completed = 0
        for future in as_completed(futures):
            symbol = futures[future]
            records[symbol].append(future.result())
            completed += 1
            if completed % 100 == 0 or completed == len(jobs):
                print(f"downloaded/verified {completed}/{len(jobs)} archives", flush=True)
    summaries = {symbol: normalize_symbol(symbol, records[symbol], raw_root, normalized_root)
                 for symbol in symbols}
    violations = sum(summary[key] for summary in summaries.values()
                     for key in ("conflicting_duplicates", "schema_violations", "level_violations",
                                 "numeric_violations", "incomplete_snapshots"))
    adequate = all(summary["normalized_rows"] >= 250_000 for summary in summaries.values())
    manifest = {"task": "TASK-0109", "source": common.DATA_URL,
                "requested_start": start.isoformat(), "requested_end": end.isoformat(),
                "normalization": "last complete snapshot per five-minute UTC bucket; no fill",
                "symbols": summaries,
                "archives": {symbol: sorted(records[symbol], key=lambda item: item["key"])
                             for symbol in symbols},
                "gate": {"integrity_violations": violations, "adequate_coverage": adequate,
                         "verdict": "KEEP" if violations == 0 and adequate else "REJECT"}}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def normalize_only(output_root: Path) -> dict[str, Any]:
    manifest_path = output_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest["archives"]
    summaries = {
        symbol: normalize_symbol(symbol, items, output_root / "raw", output_root / "normalized")
        for symbol, items in records.items()
    }
    violations = sum(summary[key] for summary in summaries.values()
                     for key in ("conflicting_duplicates", "schema_violations", "level_violations",
                                 "numeric_violations", "incomplete_snapshots"))
    adequate = all(summary["normalized_rows"] >= 250_000 for summary in summaries.values())
    manifest["symbols"] = summaries
    manifest["gate"] = {"integrity_violations": violations, "adequate_coverage": adequate,
                        "verdict": "KEEP" if violations == 0 and adequate else "REJECT"}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="data/research/bookdepth")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    parser.add_argument("--start", type=date.fromisoformat, default=START)
    parser.add_argument("--end", type=date.fromisoformat, default=END)
    parser.add_argument("--normalize-only", action="store_true")
    args = parser.parse_args()
    report = normalize_only(Path(args.output_root)) if args.normalize_only else build(
        Path(args.output_root), args.workers, tuple(args.symbols), args.start, args.end
    )
    print(json.dumps({"task": report["task"], "symbols": report["symbols"],
                      "gate": report["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
